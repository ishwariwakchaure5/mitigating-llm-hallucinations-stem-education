import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_text = Column(Text, nullable=False)
    verdict = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    path_a_score = Column(Float, nullable=True)
    path_b_score = Column(Float, nullable=True)
    path_c_score = Column(Float, nullable=True)
    conflict_score = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)
    units = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    kb = relationship("KnowledgeBase", back_populates="verifications")
