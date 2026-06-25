import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.models.verification import Verification
from app.schemas.verify import VerifyRequest, VerifyResponse
from app.services.auth_service import get_current_user
from app.services.claim_decomposer import ClaimDecomposer, ClaimUnit
from app.services.embedder import TextEmbedder
from app.services.equation_store import EquationStore
from app.services.fusion import DSFusion, FusionResult
from app.services.semantic_verifier import SemanticVerifier, SemanticResult
from app.services.symbolic_verifier import SymbolicVerifier, SymbolicResult
from app.services.visual_store import VisualStore
from app.services.visual_verifier import VisualVerifier, VisualResult

router = APIRouter()
logger = logging.getLogger(__name__)

def _weighted_verdict(unit_results: list[dict]) -> tuple[str, float, str]:
    """Weighted-confidence voting across all claim units.

    Returns (overall_verdict, overall_confidence, explanation).
    """
    if not unit_results:
        return "uncertain", 0.0, "Insufficient evidence to verify these claims."

    correct_units   = [u for u in unit_results if u["verdict"] == "correct"]
    wrong_units     = [u for u in unit_results if u["verdict"] == "wrong"]
    uncertain_units = [u for u in unit_results if u["verdict"] == "uncertain"]

    correct_weight   = sum(u["confidence"] for u in correct_units)
    wrong_weight     = sum(u["confidence"] for u in wrong_units)
    uncertain_weight = sum(u["confidence"] for u in uncertain_units)
    total_weight     = correct_weight + wrong_weight + uncertain_weight + 0.0001

    correct_ratio = correct_weight / total_weight
    wrong_ratio   = wrong_weight   / total_weight

    if wrong_ratio >= 0.50:
        verdict = "wrong"
    elif wrong_ratio >= 0.20 and correct_ratio >= 0.40:
        verdict = "mixed"
    elif correct_ratio >= 0.60:
        verdict = "correct"
    elif wrong_ratio > 0:
        verdict = "mixed"
    else:
        verdict = "uncertain"

    # Confidence: fraction correct for mixed; highest matching-verdict unit otherwise
    if verdict == "mixed":
        confidence = round(correct_ratio, 3)
    elif verdict == "correct" and correct_units:
        confidence = max(u["confidence"] for u in correct_units)
    elif verdict == "wrong" and wrong_units:
        confidence = max(u["confidence"] for u in wrong_units)
    elif verdict == "uncertain" and uncertain_units:
        confidence = max(u["confidence"] for u in uncertain_units)
    else:
        confidence = 0.0

    n_total   = len(unit_results)
    n_correct = len(correct_units)
    n_wrong   = len(wrong_units)

    if verdict == "mixed":
        explanation = (
            f"{n_correct}/{n_total} claims supported, "
            f"{n_wrong}/{n_total} contradicted by the knowledge base. "
            f"Review the highlighted wrong units below."
        )
    elif verdict == "correct":
        explanation = (
            f"All {n_total} claims are supported by the knowledge base."
            if n_wrong == 0
            else f"{n_correct}/{n_total} claims supported. Minor uncertainties present."
        )
    elif verdict == "wrong":
        explanation = f"{n_wrong}/{n_total} claims contradict the knowledge base."
    else:
        explanation = "Insufficient evidence to verify these claims."

    return verdict, confidence, explanation


# ── helpers for safe parallel execution ──────────────────────────────────────

def _safe_semantic(verifier: SemanticVerifier, unit: ClaimUnit, kb_id: str) -> SemanticResult:
    try:
        return verifier.verify(unit, kb_id)
    except Exception as e:
        logger.warning("Path A failed for unit %s: %s", unit.unit_id, e)
        return SemanticResult()


def _safe_symbolic(verifier: SymbolicVerifier, unit: ClaimUnit, kb_id: str) -> SymbolicResult:
    try:
        return verifier.verify(unit, kb_id)
    except Exception as e:
        logger.warning("Path B failed for unit %s: %s", unit.unit_id, e)
        return SymbolicResult()


def _safe_visual(verifier: VisualVerifier, unit: ClaimUnit, kb_id: str) -> VisualResult:
    try:
        return verifier.verify(unit, kb_id)
    except Exception as e:
        logger.warning("Path C failed for unit %s: %s", unit.unit_id, e)
        return VisualResult()


# ── POST /verify/{kb_id} ──────────────────────────────────────────────────────

@router.post("/{kb_id}", response_model=VerifyResponse, status_code=201)
async def verify_claim(
    kb_id: UUID,
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Ownership + readiness check
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if kb.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Knowledge base is not ready for verification (status: {kb.status})",
        )

    # 2. Decompose claim into atomic units
    decomposer = ClaimDecomposer()
    units = decomposer.decompose(body.claim_text)
    logger.info("Decomposed claim into %d unit(s)", len(units))

    # 3. Instantiate verifiers (heavy singletons loaded lazily inside each)
    embedder = TextEmbedder()
    eq_store = EquationStore()
    vis_store = VisualStore()
    sem_verifier = SemanticVerifier(embedder)
    sym_verifier = SymbolicVerifier(eq_store)
    vis_verifier = VisualVerifier(vis_store)
    fusion = DSFusion()

    kb_str = str(kb_id)
    unit_results = []
    fused_results: list[FusionResult] = []
    all_evidence: list[dict] = []
    seen_chunk_ids: set[str] = set()

    # 4 & 5. Run 3 paths concurrently per unit, fuse, collect evidence
    for unit in units:
        with ThreadPoolExecutor(max_workers=3) as pool:
            fut_a = pool.submit(_safe_semantic, sem_verifier, unit, kb_str)
            fut_b = pool.submit(_safe_symbolic, sym_verifier, unit, kb_str)
            fut_c = pool.submit(_safe_visual, vis_verifier, unit, kb_str)
            ra: SemanticResult = fut_a.result()
            rb: SymbolicResult = fut_b.result()
            rc: VisualResult = fut_c.result()

        fused: FusionResult = fusion.fuse(ra, rb, rc)
        fused_results.append(fused)

        unit_results.append(
            {
                "unit_id": unit.unit_id,
                "text": unit.text,
                "unit_type": unit.unit_type,
                "verdict": fused.verdict,
                "confidence": fused.confidence,
                "path_a_score": fused.path_a_score,
                "path_b_score": fused.path_b_score,
                "path_c_score": fused.path_c_score,
                "conflict_score": fused.conflict_score,
                "explanation": fused.explanation,
                "evidence": ra.evidence_chunks[:3],
            }
        )

        # Collect deduplicated evidence from Path A
        for chunk in ra.evidence_chunks:
            cid = chunk.get("chunk_id")
            if cid and cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                all_evidence.append(chunk)

    # 6. Weighted-confidence voting for overall verdict
    overall_verdict, overall_confidence, explanation = _weighted_verdict(unit_results)

    # Average path / conflict scores across all units
    n = len(fused_results)
    avg_a       = round(sum(f.path_a_score   for f in fused_results) / n, 3)
    avg_b       = round(sum(f.path_b_score   for f in fused_results) / n, 3)
    avg_c       = round(sum(f.path_c_score   for f in fused_results) / n, 3)
    avg_conflict = round(sum(f.conflict_score for f in fused_results) / n, 3)

    # 7. Persist to DB
    verification = Verification(
        kb_id=kb_id,
        claim_text=body.claim_text,
        verdict=overall_verdict,
        confidence=overall_confidence,
        path_a_score=avg_a,
        path_b_score=avg_b,
        path_c_score=avg_c,
        conflict_score=avg_conflict,
        explanation=explanation,
        units=unit_results,
        evidence=all_evidence[:10],
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)

    return verification


# ── GET /verify/{kb_id}/history ───────────────────────────────────────────────

@router.get("/{kb_id}/history", response_model=list[VerifyResponse])
async def get_history(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    hist = await db.execute(
        select(Verification)
        .where(Verification.kb_id == kb_id)
        .order_by(Verification.created_at.desc())
        .limit(20)
    )
    return hist.scalars().all()
