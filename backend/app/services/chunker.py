import re
import uuid
import logging
from dataclasses import dataclass, field
from typing import List
from app.services.document_parser import ParsedDocument, EQUATION_PATTERNS

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    kb_id: str
    text: str
    page_number: int
    chunk_index: int
    has_equations: bool
    equation_strings: List[str] = field(default_factory=list)
    block_type: str = "text"


class SemanticChunker:
    CHUNK_SIZE = 400   # max words per chunk window
    OVERLAP = 50       # words of overlap carried into the next window

    def create_chunks(self, parsed: ParsedDocument, kb_id: str) -> List[Chunk]:
        chunks: List[Chunk] = []
        idx = 0
        for block in parsed.text_blocks:
            text = block.text.strip()
            if len(text) < 5:
                continue
            sentences = self._split_sentences(text)
            windows = self._make_windows(sentences)
            for window_text in windows:
                if not window_text.strip():
                    continue
                eqs = self._extract_equations(window_text)
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=parsed.document_id,
                        kb_id=kb_id,
                        text=window_text,
                        page_number=block.page_number,
                        chunk_index=idx,
                        has_equations=len(eqs) > 0,
                        equation_strings=eqs,
                        block_type=block.block_type,
                    )
                )
                idx += 1
        return chunks

    # ── helpers ───────────────────────────────────────────────────────────────

    def _split_sentences(self, text: str) -> List[str]:
        # Split on sentence-ending punctuation OR on newlines (for equation lines,
        # headings, and table rows that don't end with punctuation).
        parts = re.split(r'(?<=[.!?])\s+|\n+', text)
        # Keep only segments that are meaningful (> 10 chars OR contain an equation marker)
        return [
            s.strip()
            for s in parts
            if s.strip() and (len(s.strip()) > 10 or '$' in s or '\\' in s)
        ]

    def _make_windows(self, sentences: List[str]) -> List[str]:
        if not sentences:
            return []
        windows: List[str] = []
        current: List[str] = []
        current_len = 0
        for sent in sentences:
            words = sent.split()
            if current_len + len(words) > self.CHUNK_SIZE and current:
                windows.append(" ".join(current))
                overlap = (
                    current[-self.OVERLAP:]
                    if len(current) > self.OVERLAP
                    else current
                )
                current = overlap + words
                current_len = len(current)
            else:
                current.extend(words)
                current_len += len(words)
        if current:
            windows.append(" ".join(current))
        return windows

    def _extract_equations(self, text: str) -> List[str]:
        found: List[str] = []
        for pattern in EQUATION_PATTERNS:
            found.extend(re.findall(pattern, text, re.DOTALL))
        return list(set(found))
