from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class VerifyRequest(BaseModel):
    claim_text: str
    image_base64: Optional[str] = None


class UnitResult(BaseModel):
    unit_id: str
    text: str
    unit_type: str
    verdict: str
    confidence: float
    evidence: List[dict] = []


class VerifyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kb_id: UUID
    claim_text: str
    verdict: str  # correct | wrong | uncertain | mixed
    confidence: float
    conflict_score: float
    path_a_score: float
    path_b_score: float
    path_c_score: float
    explanation: str
    units: List[dict]
    evidence: List[dict]
    created_at: datetime
