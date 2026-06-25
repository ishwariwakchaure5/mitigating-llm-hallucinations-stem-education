import re
import uuid
import logging
from dataclasses import dataclass, field
from typing import List
from app.services.document_parser import EQUATION_PATTERNS

logger = logging.getLogger(__name__)

# Matches ONLY "X = Y op Z" forms (e.g. "F = m/a", "v = d/t", "PV = nR*T")
# where both sides are short variable names and op is exactly * or /.
# Will NOT match "R = 8.314" (number RHS) or "nRT" (no equals sign).
_PLAIN_MATH_RE = re.compile(
    r'\b([A-Za-z_]\w{0,3})\s*=\s*([A-Za-z_]\w{0,3}[\*/][A-Za-z_]\w{0,3})\b'
)

# Numeric constant tokens that should never appear in extracted equations
_SKIP_TOKENS = {"8.314", "9.8", "6.626", "1.38", "3.0"}


@dataclass
class ClaimUnit:
    unit_id: str
    text: str
    unit_type: str  # text | math | mixed
    latex_equations: List[str] = field(default_factory=list)


class ClaimDecomposer:
    def decompose(self, claim_text: str) -> List[ClaimUnit]:
        sentences = re.split(r'(?<=[.!?\n])\s+', claim_text.strip())
        units: List[ClaimUnit] = []
        for sent in sentences:
            sent = sent.strip()
            if not sent or len(sent) < 10:
                continue
            eqs = self._extract_equations(sent)
            if not eqs:
                eqs = self._extract_plain_math(sent)
            if eqs and len(sent.split()) < 15:
                utype = "math"
            elif eqs:
                utype = "mixed"
            else:
                utype = "text"
            units.append(
                ClaimUnit(
                    unit_id=str(uuid.uuid4()),
                    text=sent,
                    unit_type=utype,
                    latex_equations=eqs,
                )
            )

        # Merge very short trailing units into the previous one
        merged: List[ClaimUnit] = []
        for u in units:
            if merged and len(u.text.split()) < 8:
                merged[-1].text += " " + u.text
                merged[-1].latex_equations += u.latex_equations
            else:
                merged.append(u)

        return merged or [
            ClaimUnit(
                unit_id=str(uuid.uuid4()),
                text=claim_text,
                unit_type="text",
            )
        ]

    def _extract_equations(self, text: str) -> List[str]:
        found: List[str] = []
        for pattern in EQUATION_PATTERNS:
            found.extend(re.findall(pattern, text, re.DOTALL))
        return list(set(found))

    def _extract_plain_math(self, text: str) -> List[str]:
        """Fallback: find plain-text "X = Y op Z" math (e.g. "F = m/a", "v = d/t").

        Strict rules prevent fragments like "R = 8.314" or multi-term expressions
        like "PV = nRT" (no binary operator) from being treated as equations.
        """
        normalised = (
            text
            .replace(" divided by ", "/")
            .replace(" times ", "*")
            .replace(" multiplied by ", "*")
        )
        found = []
        for m in _PLAIN_MATH_RE.finditer(normalised):
            expr = m.group(0).strip()
            lhs = m.group(1)
            rhs = m.group(2)

            # Both sides must contain at least one letter (no pure-number sides)
            if not any(c.isalpha() for c in lhs):
                continue
            if not any(c.isalpha() for c in rhs):
                continue

            # Right side must contain exactly one binary operator (* or /)
            op_count = rhs.count('*') + rhs.count('/')
            if op_count != 1:
                continue

            # Total expression must be 3–15 characters
            if not (3 <= len(expr) <= 15):
                continue

            # Skip if any known numeric constant appears anywhere in the expression
            if any(tok in expr for tok in _SKIP_TOKENS):
                continue

            found.append(expr)
        return found
