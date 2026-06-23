import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class QuestionSetItem(Base):
    """
    SQLAlchemy model representing the question_set_items association table.
    Links questions to predefined sets with custom ordering.
    """

    __tablename__ = "question_set_items"

    question_set_id = Column(
        UUID(as_uuid=True),
        ForeignKey("question_sets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position = Column(Integer, nullable=True)

    # Relationships
    question_set = relationship("QuestionSet", back_populates="items")
    question = relationship("Question")

    def __repr__(self) -> str:
        return f"<QuestionSetItem set_id={self.question_set_id} question_id={self.question_id} position={self.position}>"


class QuestionSet(Base):
    """
    SQLAlchemy model representing the question_sets table.
    Groups predefined question packages under a user/topic scope.
    """

    __tablename__ = "question_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    generation_scope = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Composite Index for isolation scoping
    __table_args__ = (Index("idx_question_sets_user_topic", "user_id", "topic_id"),)

    # Relationships
    user = relationship("User")
    topic = relationship("Topic", back_populates="question_sets")
    items = relationship(
        "QuestionSetItem", back_populates="question_set", cascade="all, delete-orphan"
    )
    exam_sessions = relationship("ExamSession", back_populates="question_set")

    def __repr__(self) -> str:
        return f"<QuestionSet name={self.name} topic_id={self.topic_id}>"
