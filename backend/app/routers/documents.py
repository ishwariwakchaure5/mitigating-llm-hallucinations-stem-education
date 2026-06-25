import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/{doc_id}/status")
async def get_document_status(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify owning KB belongs to current user
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == doc.kb_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": str(doc.id),
        "status": doc.status,
        "error_message": doc.error_message,
    }


@router.post("/{doc_id}/reprocess", status_code=202)
async def reprocess_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == doc.kb_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if doc.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Document is '{doc.status}'; only pending or failed can be reprocessed",
        )

    doc.status = "pending"
    doc.error_message = None
    await db.commit()

    from app.tasks.dispatch import dispatch_document_processing

    dispatch_document_processing(str(doc.id))
    return {"id": str(doc.id), "status": "pending"}


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == doc.kb_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb or kb.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Remove file from disk (best-effort)
    try:
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except OSError:
        pass

    await db.delete(doc)
    await db.commit()
