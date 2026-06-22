import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Topic(Base):
    """
    SQLAlchemy model representing the topics table.
    A topic scopes datasets, tags, and questions for a user.
    """
    __tablename__ = "topics"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    name = Column(
        String, 
        nullable=False
    )
    description = Column(
        Text, 
        nullable=True
    )
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="topics")
    documents = relationship("Document", back_populates="topic", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="topic", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="topic", cascade="all, delete-orphan")
    question_sets = relationship("QuestionSet", back_populates="topic", cascade="all, delete-orphan")
    exam_sessions = relationship("ExamSession", back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Topic name={self.name} user_id={self.user_id}>"
