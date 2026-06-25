import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, update, func

from app.tasks import celery_app
from app.config import settings
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


def _make_session():
    engine = create_async_engine(settings.database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


async def run_document_processing(document_id: str) -> None:
    # Import heavy services lazily so they are loaded inside the worker process,
    # not at module import time (keeps startup fast and avoids fork issues).
    from app.services.document_parser import DocumentParser
    from app.services.chunker import SemanticChunker
    from app.services.embedder import TextEmbedder
    from app.services.equation_store import EquationStore
    from app.services.visual_store import VisualStore

    SessionLocal = _make_session()

    async with SessionLocal() as db:
        try:
            result = await db.execute(
                select(Document).where(Document.id == UUID(document_id))
            )
            doc = result.scalar_one_or_none()
            if not doc:
                logger.error("Document %s not found", document_id)
                return

            doc.status = "processing"
            await db.commit()
            logger.info("Processing: %s", doc.original_name)

            # ── 1. Parse ──────────────────────────────────────────────
            parser = DocumentParser()
            parsed = parser.parse_document(doc)
            logger.info(
                "Parsed: %d pages, %d text blocks, %d images",
                parsed.page_count,
                len(parsed.text_blocks),
                len(parsed.image_blocks),
            )

            # ── 2. Chunk ──────────────────────────────────────────────
            chunker = SemanticChunker()
            chunks = chunker.create_chunks(parsed, str(doc.kb_id))
            logger.info("Chunked: %d chunks", len(chunks))

            # ── 3. Dense text embeddings → Qdrant ─────────────────────
            embedder = TextEmbedder()
            chunk_count = embedder.embed_and_index_chunks(chunks, str(doc.kb_id))
            logger.info("Embedded: %d chunks in Qdrant", chunk_count)

            # ── 4. Equation graph ─────────────────────────────────────
            eq_store = EquationStore()
            eq_count = eq_store.extract_and_index(chunks, str(doc.kb_id))
            logger.info("Equations indexed: %d", eq_count)

            # ── 5. Visual embeddings → Qdrant ─────────────────────────
            vis_store = VisualStore()
            vis_count = vis_store.index_visuals(parsed, str(doc.kb_id))
            logger.info("Visuals indexed: %d", vis_count)

            # ── 6. Mark document ready ────────────────────────────────
            doc.status = "ready"
            doc.page_count = parsed.page_count
            await db.commit()

            # ── 7. Update KB counters ─────────────────────────────────
            ready_doc_count = await db.scalar(
                select(func.count(Document.id)).where(
                    Document.kb_id == doc.kb_id,
                    Document.status == "ready",
                )
            )
            await db.execute(
                update(KnowledgeBase)
                .where(KnowledgeBase.id == doc.kb_id)
                .values(
                    doc_count=ready_doc_count or 0,
                    chunk_count=KnowledgeBase.chunk_count + chunk_count,
                    equation_count=KnowledgeBase.equation_count + eq_count,
                    diagram_count=KnowledgeBase.diagram_count + vis_count,
                    status="ready",
                )
            )
            await db.commit()
            logger.info("Document %s fully processed and ready.", document_id)

        except Exception as exc:
            logger.error(
                "Processing failed for %s: %s", document_id, exc, exc_info=True
            )
            async with SessionLocal() as db2:
                r = await db2.execute(
                    select(Document).where(Document.id == UUID(document_id))
                )
                d = r.scalar_one_or_none()
                if d:
                    d.status = "failed"
                    d.error_message = str(exc)[:500]
                    await db2.commit()
            raise


def run_document_processing_sync(document_id: str) -> dict:
    asyncio.run(run_document_processing(document_id))
    return {"document_id": document_id, "status": "ready"}


@celery_app.task(name="vera.tasks.process_document", bind=True, max_retries=3)
def process_document(self, document_id: str) -> dict:
    try:
        return run_document_processing_sync(document_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
