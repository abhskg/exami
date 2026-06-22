import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class ExamSession(Base):
    """
    SQLAlchemy model representing the exam_sessions table.
    Tracks exam session state, settings, timing, and score logging.
    """
    __tablename__ = "exam_sessions"

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
    topic_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("topics.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    question_set_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("question_sets.id", ondelete="SET NULL"), 
        nullable=True
    )
    mode = Column(
        String, 
        nullable=False
    )  # 'practice', 'timed'
    tag_filter = Column(
        JSON, 
        nullable=True
    )
    difficulty_filter = Column(
        String, 
        nullable=True
    )
    question_count = Column(
        Integer, 
        nullable=False
    )
    time_limit_seconds = Column(
        Integer, 
        nullable=True
    )
    status = Column(
        String, 
        default="in_progress", 
        nullable=False
    )  # 'in_progress', 'completed', 'abandoned'
    started_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    completed_at = Column(
        DateTime, 
        nullable=True
    )
    score = Column(
        Float, 
        nullable=True
    )

    # Composite Index for isolation scoping and performance queries
    __table_args__ = (
        Index("idx_exam_sessions_user_topic_status", "user_id", "topic_id", "status"),
    )

    # Relationships
    user = relationship("User")
    topic = relationship("Topic", back_populates="exam_sessions")
    question_set = relationship("QuestionSet", back_populates="exam_sessions")
    responses = relationship("ExamResponse", back_populates="exam_session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ExamSession id={self.id} user_id={self.user_id} mode={self.mode} status={self.status}>"


class ExamResponse(Base):
    """
    SQLAlchemy model representing the exam_responses table.
    Tracks answers submitted by the user during an exam session.
    """
    __tablename__ = "exam_responses"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        nullable=False
    )
    exam_session_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("exam_sessions.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    question_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("questions.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    selected_option_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("question_options.id", ondelete="SET NULL"), 
        nullable=True
    )
    is_correct = Column(
        Boolean, 
        nullable=False
    )
    time_taken_seconds = Column(
        Integer, 
        nullable=True
    )
    answered_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    exam_session = relationship("ExamSession", back_populates="responses")
    question = relationship("Question", back_populates="exam_responses")
    selected_option = relationship("QuestionOption")

    def __repr__(self) -> str:
        return f"<ExamResponse id={self.id} exam_session_id={self.exam_session_id} correct={self.is_correct}>"
