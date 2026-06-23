import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

# Many-to-many association table between Questions and Tags
question_tags = Table(
    "question_tags",
    Base.metadata,
    Column(
        "question_id",
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class Question(Base):
    """
    SQLAlchemy model representing the questions table.
    Stores generated/manually created practice questions.
    """

    __tablename__ = "questions"

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
    source_chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("content_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    question_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String, default="medium", nullable=False)  # 'easy', 'medium', 'hard'
    generated_by = Column(String, default="ai", nullable=False)  # 'ai', 'manual'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Composite Index for isolation scoping
    __table_args__ = (Index("idx_questions_user_topic", "user_id", "topic_id"),)

    # Relationships
    user = relationship("User")
    topic = relationship("Topic", back_populates="questions")
    source_chunk = relationship("ContentChunk", back_populates="questions")
    options = relationship(
        "QuestionOption", back_populates="question", cascade="all, delete-orphan"
    )
    tags = relationship("Tag", secondary=question_tags, back_populates="questions")
    exam_responses = relationship("ExamResponse", back_populates="question")

    def __repr__(self) -> str:
        return f"<Question id={self.id} difficulty={self.difficulty} active={self.is_active}>"


class QuestionOption(Base):
    """
    SQLAlchemy model representing the question_options table.
    Stores multiple choice options for questions.
    """

    __tablename__ = "question_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    option_order = Column(Integer, nullable=False)

    # Relationships
    question = relationship("Question", back_populates="options")

    def __repr__(self) -> str:
        return f"<QuestionOption id={self.id} question_id={self.question_id} correct={self.is_correct}>"
