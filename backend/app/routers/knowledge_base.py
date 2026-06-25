import os
import logging
from uuid import uuid4, UUID
from typing import List

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.user import User
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseResponse
from app.schemas.document import DocumentResponse
from app.services.auth_service import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".docx", ".jpg", ".jpeg", ".png", ".heic"}
EXT_TO_TYPE = {
    ".pdf": "pdf",
    ".pptx": "pptx",
    ".docx": "docx",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".heic": "image",
}


async def _get_owned_kb(kb_id: UUID, db: AsyncSession, current_user: User) -> KnowledgeBase:
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return kb


# ── LIST ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=dict)
async def list_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == current_user.id)
        .order_by(KnowledgeBase.created_at.desc())
    )
    kbs = result.scalars().all()
    return {
        "items": [KnowledgeBaseResponse.model_validate(kb) for kb in kbs],
        "total": len(kbs),
    }


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = KnowledgeBase(
        user_id=current_user.id,
        name=data.name,
        subject=data.subject,
        description=data.description,
        status="empty",
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return KnowledgeBaseResponse.model_validate(kb)


# ── GET ───────────────────────────────────────────────────────────────────────

@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await _get_owned_kb(kb_id, db, current_user)
    return KnowledgeBaseResponse.model_validate(kb)


# ── DELETE ────────────────────────────────────────────────────────────────────

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await _get_owned_kb(kb_id, db, current_user)

    # Remove Qdrant collections if they exist — failure is non-fatal
    try:
        from qdrant_client import QdrantClient
        qclient = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        for suffix in ("text", "visual"):
            col = f"stem_{kb_id}_{suffix}"
            try:
                qclient.delete_collection(col)
                logger.info("Deleted Qdrant collection %s", col)
            except Exception:
                pass  # collection may not exist yet
    except Exception as e:
        logger.warning("Qdrant cleanup skipped: %s", e)

    await db.delete(kb)
    await db.commit()
    return {"message": "deleted"}


# ── LIST DOCUMENTS ────────────────────────────────────────────────────────────

@router.get("/{kb_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_kb(kb_id, db, current_user)
    result = await db.execute(
        select(Document)
        .where(Document.kb_id == kb_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


# ── UPLOAD ────────────────────────────────────────────────────────────────────

@router.post("/{kb_id}/upload", status_code=202)
async def upload_documents(
    kb_id: UUID,
    response: Response,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await _get_owned_kb(kb_id, db, current_user)

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    created: List[DocumentResponse] = []
    doc_ids_to_dispatch: List[str] = []
    errors: List[str] = []

    dir_path = os.path.join(settings.upload_dir, str(kb_id))
    os.makedirs(dir_path, exist_ok=True)

    for upload_file in files:
        fname = upload_file.filename or "unknown"
        ext = os.path.splitext(fname)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{fname}: unsupported extension '{ext}'")
            continue

        content = await upload_file.read()
        if len(content) > max_bytes:
            errors.append(
                f"{fname}: exceeds {settings.max_file_size_mb} MB limit "
                f"({len(content) // (1024*1024)} MB)"
            )
            continue

        stored_filename = f"{uuid4()}_{fname}"
        file_path = os.path.join(dir_path, stored_filename)

        async with aiofiles.open(file_path, "wb") as fout:
            await fout.write(content)

        doc = Document(
            kb_id=kb_id,
            filename=stored_filename,
            original_name=fname,
            file_type=EXT_TO_TYPE[ext],
            file_path=file_path,
            file_size=len(content),
            status="pending",
        )
        db.add(doc)
        await db.flush()  # get doc.id before commit

        doc_ids_to_dispatch.append(str(doc.id))
        created.append(DocumentResponse.model_validate(doc))

    # Commit all documents first so the task can find them in the DB
    if created:
        kb.doc_count = (
            await db.scalar(
                select(func.count(Document.id)).where(Document.kb_id == kb_id)
            )
        ) or 0
        if kb.status == "empty":
            kb.status = "processing"
        await db.commit()

        # Dispatch processing only AFTER the DB transaction is committed
        from app.tasks.dispatch import dispatch_document_processing

        for doc_id in doc_ids_to_dispatch:
            dispatch_document_processing(doc_id)

    if errors:
        response.headers["X-Upload-Errors"] = "; ".join(errors)

    return {"documents": created, "errors": errors}
