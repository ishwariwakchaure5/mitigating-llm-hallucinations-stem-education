import uuid
import logging
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from app.config import settings
from app.services.chunker import Chunk

logger = logging.getLogger(__name__)

# Module-level singleton — loaded once, shared across Celery worker tasks
_bge_model = None


def get_bge_model():
    """Return the nomic-embed-text-v1 SentenceTransformer, loading it on first call."""
    global _bge_model
    if _bge_model is None:
        logger.info(
            "Loading nomic-embed-text model (first time: downloads ~500 MB)..."
        )
        from sentence_transformers import SentenceTransformer

        _bge_model = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1", trust_remote_code=True
        )
        logger.info("nomic-embed-text loaded.")
    return _bge_model


class TextEmbedder:
    EMBED_DIM = 768
    BATCH_SIZE = 16

    def __init__(self) -> None:
        self.qdrant = QdrantClient(
            host=settings.qdrant_host, port=settings.qdrant_port
        )

    # ── collection management ─────────────────────────────────────────────────

    def ensure_collection(self, kb_id: str) -> str:
        """Create the Qdrant collection for this KB if it does not exist yet."""
        name = f"stem_{kb_id}_text"
        existing = {c.name for c in self.qdrant.get_collections().collections}
        if name not in existing:
            self.qdrant.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=self.EMBED_DIM, distance=Distance.COSINE
                ),
            )
            logger.info("Created Qdrant collection: %s", name)
        return name

    # ── indexing ──────────────────────────────────────────────────────────────

    def embed_and_index_chunks(self, chunks: List[Chunk], kb_id: str) -> int:
        """Embed each chunk and upsert into Qdrant. Returns the number of vectors stored."""
        if not chunks:
            return 0

        model = get_bge_model()
        collection = self.ensure_collection(kb_id)
        total = 0

        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]
            texts = [c.text for c in batch]
            vecs = model.encode(
                texts, normalize_embeddings=True, show_progress_bar=False
            ).tolist()

            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=v,
                    payload={
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "kb_id": c.kb_id,
                        "text": c.text,
                        "page_number": c.page_number,
                        "has_equations": c.has_equations,
                        "block_type": c.block_type,
                    },
                )
                for c, v in zip(batch, vecs)
            ]
            self.qdrant.upsert(collection_name=collection, points=points)
            total += len(batch)
            logger.info("Indexed batch %d–%d into %s", i, i + len(batch), collection)

        return total

    # ── search ────────────────────────────────────────────────────────────────

    def search(self, query: str, kb_id: str, top_k: int = 8) -> List[dict]:
        """Dense cosine search over the KB's text collection."""
        model = get_bge_model()
        vec = model.encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        )[0].tolist()
        results = self.qdrant.search(
            collection_name=f"stem_{kb_id}_text",
            query_vector=vec,
            limit=top_k,
            with_payload=True,
        )
        return [{"score": r.score, **r.payload} for r in results]
