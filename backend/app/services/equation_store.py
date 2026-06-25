import os
import uuid
import pickle
import logging
import networkx as nx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sympy import sympify, simplify
from app.config import settings
from app.services.chunker import Chunk

logger = logging.getLogger(__name__)


@dataclass
class EqNode:
    eq_id: str
    kb_id: str
    document_id: str
    page_number: int
    latex_string: str
    sympy_str: str
    canonical_hash: str
    variables: List[str]


class EquationStore:
    # Per-process in-memory graph cache; keyed by kb_id
    _graph_cache: Dict[str, nx.DiGraph] = {}

    # ── persistence ───────────────────────────────────────────────────────────

    def _graph_path(self, kb_id: str) -> str:
        return os.path.join(settings.upload_dir, str(kb_id), "eq_graph.pkl")

    def _load(self, kb_id: str) -> nx.DiGraph:
        if kb_id in self._graph_cache:
            return self._graph_cache[kb_id]
        path = self._graph_path(kb_id)
        if os.path.exists(path):
            with open(path, "rb") as fh:
                g = pickle.load(fh)
        else:
            g = nx.DiGraph()
        self._graph_cache[kb_id] = g
        return g

    def _save(self, kb_id: str, g: nx.DiGraph) -> None:
        path = self._graph_path(kb_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump(g, fh)
        self._graph_cache[kb_id] = g

    # ── latex / sympy helpers ─────────────────────────────────────────────────

    def latex_to_sympy(self, latex: str) -> Optional[Any]:
        """Convert a LaTeX or plain-text math string to a SymPy expression."""
        # ── 1. latex2sympy2 (best quality, Python 3.13 incompatible) ──────────
        try:
            from latex2sympy2 import latex2sympy
            return latex2sympy(latex)
        except Exception:
            pass

        # ── 2. parse_expr with implicit multiplication ────────────────────────
        # Handles:  plain-text like "F = m/a"  AND  latex-stripped like "ma"
        # (sympify("ma") yields symbol 'ma', not m*a — parse_expr fixes this)
        try:
            from sympy import Eq as SymEq
            from sympy.parsing.sympy_parser import (
                parse_expr,
                standard_transformations,
                implicit_multiplication_application,
            )
            _tf = standard_transformations + (implicit_multiplication_application,)
            clean = latex.strip().strip('$').strip()
            if '=' in clean:
                lhs, rhs = clean.split('=', 1)
                return SymEq(
                    parse_expr(lhs.strip(), transformations=_tf),
                    parse_expr(rhs.strip(), transformations=_tf),
                )
            return parse_expr(clean, transformations=_tf)
        except Exception:
            pass

        # ── 3. Final fallback: store as latex-hash (counted but not matchable) ─
        return None

    def canonical_hash(self, expr: Any) -> str:
        try:
            return str(hash(str(simplify(expr))))
        except Exception:
            return str(hash(str(expr)))

    # ── indexing ──────────────────────────────────────────────────────────────

    def extract_and_index(self, chunks: List[Chunk], kb_id: str) -> int:
        """Parse equations from chunks and add them as nodes to the equation graph."""
        g = self._load(kb_id)
        count = 0
        for chunk in chunks:
            if not chunk.has_equations:
                continue
            for latex in chunk.equation_strings:
                expr = self.latex_to_sympy(latex)
                eq_id = str(uuid.uuid4())
                # Store equation even when sympy conversion fails — use the LaTeX
                # string itself as the canonical key.  Exact-match and contradiction
                # logic will only fire when expr is not None, but counting and
                # graph-neighbour edges work with latex-hash nodes too.
                if expr is not None:
                    sympy_str    = str(expr)
                    canon_hash   = self.canonical_hash(expr)
                    variables    = [str(s) for s in expr.free_symbols]
                else:
                    sympy_str    = latex
                    canon_hash   = str(hash(latex))
                    variables    = []
                node = EqNode(
                    eq_id=eq_id,
                    kb_id=kb_id,
                    document_id=chunk.document_id,
                    page_number=chunk.page_number,
                    latex_string=latex,
                    sympy_str=sympy_str,
                    canonical_hash=canon_hash,
                    variables=variables,
                )
                g.add_node(eq_id, **node.__dict__)
                count += 1
        self._build_edges(g)
        self._save(kb_id, g)
        logger.info("Indexed %d equations for KB %s", count, kb_id)
        return count

    def _build_edges(self, g: nx.DiGraph) -> None:
        """Connect equation nodes that share free variables."""
        nodes = list(g.nodes(data=True))
        for i, (n1, d1) in enumerate(nodes):
            for n2, d2 in nodes[i + 1 :]:
                shared = set(d1.get("variables", [])) & set(d2.get("variables", []))
                if shared:
                    g.add_edge(n1, n2, shared_vars=list(shared))

    # ── retrieval ─────────────────────────────────────────────────────────────

    def find(self, kb_id: str, latex: str) -> Dict[str, Any]:
        """
        Search the equation graph for a match.
        Returns a dict with keys: match ('exact'|'contradiction'|'none'), confidence, node/kb_node.
        """
        g = self._load(kb_id)
        expr = self.latex_to_sympy(latex)
        if expr is None:
            return {"match": "none", "confidence": 0.0}

        chash = self.canonical_hash(expr)

        # Exact match via canonical hash
        for nid, data in g.nodes(data=True):
            if data.get("canonical_hash") == chash:
                return {"match": "exact", "confidence": 1.0, "node": data}

        # Contradiction check
        from sympy import Eq as SymEq
        claim_vars = set(str(s) for s in expr.free_symbols)
        for nid, data in g.nodes(data=True):
            try:
                kb_expr = sympify(data["sympy_str"])

                # GUARD: only test for contradiction when the two expressions
                # share at least one free variable.  Without shared variables,
                # SymPy simplify() can produce spurious non-zero differences
                # across completely unrelated equations (e.g. "F = m/a" vs
                # "PV = nRT") — this guard prevents those false positives.
                kb_vars = set(data.get("variables", []))
                if not claim_vars.intersection(kb_vars):
                    continue

                # For Eq objects (produced by the latex_to_sympy Eq() path):
                # contradiction = same LHS variable but structurally different RHS
                if isinstance(expr, SymEq) and isinstance(kb_expr, SymEq):
                    if simplify(expr.lhs - kb_expr.lhs) == 0:
                        if simplify(expr.rhs - kb_expr.rhs) != 0:
                            return {
                                "match": "contradiction",
                                "confidence": 0.88,
                                "kb_node": data,
                            }
                    continue

                # For plain expressions: non-zero numeric difference
                diff = simplify(expr - kb_expr)
                if diff.is_number and diff != 0:
                    return {
                        "match": "contradiction",
                        "confidence": 0.88,
                        "kb_node": data,
                    }
            except Exception:
                continue

        return {"match": "none", "confidence": 0.0}
