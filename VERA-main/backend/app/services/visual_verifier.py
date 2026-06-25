import logging
from dataclasses import dataclass, field
from typing import List
from app.services.visual_store import VisualStore
from app.services.claim_decomposer import ClaimUnit

logger = logging.getLogger(__name__)


@dataclass
class VisualResult:
    score: float = 0.0
    matched_diagrams: List[dict] = field(default_factory=list)
    verdict_contribution: str = "uncertain"


class VisualVerifier:
    def __init__(self, vis_store: VisualStore) -> None:
        self.vis_store = vis_store

    def verify(self, unit: ClaimUnit, kb_id: str) -> VisualResult:
        try:
            results = self.vis_store.search_by_text(unit.text, kb_id, top_k=5)
            if not results:
                return VisualResult()
            top = results[0]["score"]
            # CLIP ViT-B/32 scores genuine matches in 0.50-0.65 range;
            # the original 0.72 threshold was calibrated for ViT-L/14.
            verdict = "correct" if top > 0.50 else "uncertain"
            return VisualResult(
                score=top,
                matched_diagrams=results[:3],
                verdict_contribution=verdict,
            )
        except Exception as e:
            logger.warning("Visual verify failed: %s", e)
            return VisualResult()
