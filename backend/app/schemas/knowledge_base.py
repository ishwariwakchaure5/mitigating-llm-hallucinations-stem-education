from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class KnowledgeBaseCreate(BaseModel):
    name: str
    subject: str
    description: Optional[str] = None

    @field_validator("name", "subject")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 2:
            raise ValueError("Must be at least 2 characters")
        return v.strip()


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    subject: str
    description: Optional[str]
    status: str
    doc_count: int
    chunk_count: int
    equation_count: int
    diagram_count: int
    created_at: datetime
    updated_at: datetime
