"""Dispatch document processing to Celery or in-process fallback."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from app.tasks import celery_app

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="stem-process")

_worker_cache: dict[str, float | bool] = {"available": False, "checked_at": 0.0}
_WORKER_CACHE_TTL = 10.0


def _celery_worker_available() -> bool:
    now = time.monotonic()
    if now - _worker_cache["checked_at"] < _WORKER_CACHE_TTL:
        return bool(_worker_cache["available"])

    available = False
    try:
        insp = celery_app.control.inspect(timeout=1.0)
        ping = insp.ping() if insp else None
        available = bool(ping)
    except Exception as exc:
        logger.debug("Celery worker check failed: %s", exc)

    _worker_cache["available"] = available
    _worker_cache["checked_at"] = now
    return available


def _run_in_process(document_id: str) -> None:
    from app.tasks.processing import run_document_processing_sync

    try:
        run_document_processing_sync(document_id)
    except Exception:
        logger.exception("In-process processing failed for %s", document_id)


def dispatch_document_processing(document_id: str) -> None:
    """Queue via Celery when a worker is up; otherwise process in a background thread."""
    if _celery_worker_available():
        try:
            from app.tasks.processing import process_document

            process_document.delay(document_id)
            logger.info("Queued document %s for Celery processing", document_id)
            return
        except Exception as exc:
            logger.warning(
                "Celery dispatch failed for %s (%s); using in-process fallback",
                document_id,
                exc,
            )

    logger.info(
        "No Celery worker available; processing document %s in-process", document_id
    )
    _executor.submit(_run_in_process, document_id)


async def requeue_pending_documents() -> int:
    """Re-dispatch any documents left in pending (e.g. after a restart without Celery)."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from app.config import settings
    from app.models.document import Document

    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    count = 0
    async with SessionLocal() as db:
        result = await db.execute(
            select(Document.id).where(Document.status == "pending")
        )
        for doc_id in result.scalars():
            dispatch_document_processing(str(doc_id))
            count += 1

    if count:
        logger.info("Re-queued %d pending document(s) for processing", count)
    return count
