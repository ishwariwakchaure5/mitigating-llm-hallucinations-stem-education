import logging
from dataclasses import dataclass, field
from typing import List, Optional
from app.services.equation_store import EquationStore
from app.services.claim_decomposer import ClaimUnit

logger = logging.getLogger(__name__)


@dataclass
class SymbolicResult:
    score: float = 0.0
    match_type: str = "none"
    matched_node: Optional[dict] = None
    verdict_contribution: str = "uncertain"


class SymbolicVerifier:
    def __init__(self, eq_store: EquationStore) -> None:
        self.eq_store = eq_store

    def verify(self, unit: ClaimUnit, kb_id: str) -> SymbolicResult:
        # Text-only units have no symbolic content to verify
        if unit.unit_type == "text" or not unit.latex_equations:
            return SymbolicResult()

        for latex in unit.latex_equations:
            result = self.eq_store.find(kb_id, latex)
            if result["match"] == "exact":
                return SymbolicResult(
                    score=1.0,
                    match_type="exact",
                    matched_node=result.get("node"),
                    verdict_contribution="correct",
                )
            if result["match"] == "contradiction":
                return SymbolicResult(
                    score=result["confidence"],
                    match_type="contradiction",
                    matched_node=result.get("kb_node"),
                    verdict_contribution="wrong",
                )

        # No equations matched anything in the graph
        return SymbolicResult()
