import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List
from app.services.embedder import TextEmbedder
from app.services.claim_decomposer import ClaimUnit

logger = logging.getLogger(__name__)

# Module-level singleton — loaded once per process (~500 MB download on first call)
_nli_model = None


def get_nli():
    global _nli_model
    if _nli_model is None:
        logger.info("Loading NLI model (first time: downloads ~500 MB)...")
        from sentence_transformers.cross_encoder import CrossEncoder

        _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-small")
        logger.info("NLI model loaded.")
    return _nli_model


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x))
    return e / e.sum()


@dataclass
class SemanticResult:
    score: float = 0.0
    contradiction_score: float = 0.0
    evidence_chunks: List[dict] = field(default_factory=list)
    verdict_contribution: str = "uncertain"


class SemanticVerifier:
    def __init__(self, embedder: TextEmbedder) -> None:
        self.embedder = embedder

    def verify(self, unit: ClaimUnit, kb_id: str) -> SemanticResult:
        # Dense retrieval — find the most relevant chunks
        chunks = self.embedder.search(unit.text, kb_id, top_k=8)
        if not chunks or chunks[0]["score"] < 0.35:
            return SemanticResult(evidence_chunks=chunks)

        # NLI re-ranking on the top-5 retrieved chunks.
        # Use cosine-weighted aggregation so more-relevant chunks dominate the mean,
        # preventing weaker off-topic chunks from dragging entail down / contra up.
        nli = get_nli()
        nli_chunks = chunks[:5]
        pairs = [[c["text"], unit.text] for c in nli_chunks]
        try:
            raw_scores = nli.predict(pairs)
            # Output shape: (n, 3) — columns: [contradiction, neutral, entailment]
            probs = [softmax(s) for s in raw_scores]
            weights = np.array([c["score"] for c in nli_chunks])
            entail = float(np.average([p[2] for p in probs], weights=weights))
            contra = float(np.average([p[0] for p in probs], weights=weights))
        except Exception as e:
            logger.warning("NLI prediction failed: %s", e)
            # Fall back to cosine similarity as a weak entailment proxy
            entail = chunks[0]["score"] * 0.6
            contra = 0.0

        # Blend: NLI 70% + cosine similarity 30% (Fix 3 — helps borderline cases
        # where the top chunk is highly relevant but NLI score is compressed).
        cosine_top = chunks[0]["score"] if chunks else 0.0
        entail = entail * 0.70 + cosine_top * 0.30

        # Recalibrated thresholds for nli-deberta-v3-small whose scores are
        # compressed toward 0.5 compared to larger models (Fix 1a).
        if entail > 0.45:
            verdict = "correct"
        elif contra > 0.60:
            verdict = "wrong"
        else:
            verdict = "uncertain"

        return SemanticResult(
            score=entail,
            contradiction_score=contra,
            evidence_chunks=chunks,
            verdict_contribution=verdict,
        )
