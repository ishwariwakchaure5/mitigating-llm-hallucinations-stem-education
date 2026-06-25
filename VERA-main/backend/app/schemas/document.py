from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kb_id: UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int
    page_count: Optional[int]
    status: str
    error_message: Optional[str]
    created_at: datetime
