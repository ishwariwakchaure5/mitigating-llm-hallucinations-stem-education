from dataclasses import dataclass
from typing import Tuple
from app.services.semantic_verifier import SemanticResult
from app.services.symbolic_verifier import SymbolicResult
from app.services.visual_verifier import VisualResult


@dataclass
class MassFunc:
    correct: float = 0.0
    wrong: float = 0.0
    uncertain: float = 1.0

    def normalize(self) -> "MassFunc":
        total = self.correct + self.wrong + self.uncertain
        if total > 0:
            self.correct /= total
            self.wrong /= total
            self.uncertain /= total
        return self


@dataclass
class FusionResult:
    verdict: str
    confidence: float
    conflict_score: float
    path_a_score: float
    path_b_score: float
    path_c_score: float
    explanation: str


class DSFusion:
    # ── mass function constructors ────────────────────────────────────────────

    def to_mass_a(self, r: SemanticResult) -> MassFunc:
        if r.verdict_contribution == "correct":
            # Semantic verifier already decided "correct" (blended entail > threshold).
            # Do NOT feed NLI contra into the wrong slot here — residual contra mass
            # from nli-deberta-v3-small is noisy and will flip borderline correct claims
            # to wrong when Path B is silent.  Path B is the designated contradiction
            # detector; if it returns score=0 there is no real contradiction.
            return MassFunc(
                correct=r.score,
                wrong=0.0,
                uncertain=max(0.0, 1.0 - r.score),
            ).normalize()
        if r.verdict_contribution == "wrong":
            return MassFunc(
                correct=0.05,
                wrong=r.contradiction_score,
                uncertain=max(0.0, 0.95 - r.contradiction_score),
            ).normalize()
        return MassFunc()

    def to_mass_b(self, r: SymbolicResult) -> MassFunc:
        if r.match_type == "exact":
            return MassFunc(correct=0.99, wrong=0.0, uncertain=0.01)
        if r.match_type == "contradiction":
            return MassFunc(
                correct=0.01,
                wrong=r.score,
                uncertain=1 - r.score,
            ).normalize()
        return MassFunc()

    def to_mass_c(self, r: VisualResult) -> MassFunc:
        if r.verdict_contribution == "correct":
            # Amplify genuine visual matches — ViT-B/32 scores are lower than
            # ViT-L/14, so a raw score of 0.55 should carry real weight.
            amplified = min(r.score * 1.4, 0.95)
            return MassFunc(
                correct=amplified,
                wrong=0.0,
                uncertain=max(1 - amplified, 0.05),
            ).normalize()
        return MassFunc()

    # ── Dempster combination ──────────────────────────────────────────────────

    def combine(self, m1: MassFunc, m2: MassFunc) -> Tuple[MassFunc, float]:
        """Dempster's rule of combination. Returns (combined mass, conflict K)."""
        K = m1.correct * m2.wrong + m1.wrong * m2.correct
        if K >= 0.98:
            # Total conflict — fall back to maximum uncertainty
            return MassFunc(correct=0.0, wrong=0.0, uncertain=1.0), K
        norm = 1.0 / (1.0 - K)
        c = norm * (
            m1.correct * m2.correct
            + m1.correct * m2.uncertain
            + m1.uncertain * m2.correct
        )
        w = norm * (
            m1.wrong * m2.wrong
            + m1.wrong * m2.uncertain
            + m1.uncertain * m2.wrong
        )
        u = norm * (m1.uncertain * m2.uncertain)
        return MassFunc(correct=c, wrong=w, uncertain=u), K

    # ── top-level fusion ──────────────────────────────────────────────────────

    def fuse(
        self, ra: SemanticResult, rb: SymbolicResult, rc: VisualResult
    ) -> FusionResult:
        ma, mb, mc = self.to_mass_a(ra), self.to_mass_b(rb), self.to_mass_c(rc)
        fab, k1 = self.combine(ma, mb)
        fabc, k2 = self.combine(fab, mc)
        K = max(k1, k2)

        # Symbolic exact match / contradiction override everything else
        if rb.match_type == "exact":
            verdict, confidence = "correct", 0.97
        elif rb.match_type == "contradiction":
            verdict, confidence = "wrong", round(rb.score, 3)
        elif fabc.correct >= 0.50:
            verdict, confidence = "correct", round(fabc.correct, 3)
        elif fabc.wrong >= 0.50:
            verdict, confidence = "wrong", round(fabc.wrong, 3)
        else:
            verdict, confidence = "uncertain", round(1 - fabc.uncertain, 3)

        if K > 0.4:
            explanation = f"Paths disagree (conflict={K:.2f}) — treat with caution."
        else:
            explanation = f"Paths agree (conflict={K:.2f})."

        return FusionResult(
            verdict=verdict,
            confidence=confidence,
            conflict_score=round(K, 3),
            path_a_score=round(ra.score, 3),
            path_b_score=round(rb.score, 3),
            path_c_score=round(rc.score, 3),
            explanation=explanation,
        )
