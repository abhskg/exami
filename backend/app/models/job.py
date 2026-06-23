import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Job(Base):
    """
    SQLAlchemy model representing the jobs table.
    Tracks state of async tasks like document ingestion.
    """

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        String, default="pending", nullable=False
    )  # e.g., 'pending', 'running', 'completed', 'failed'
    task_type = Column(String, nullable=False)  # e.g., 'document_ingestion'
    progress = Column(Integer, default=0, nullable=False)  # 0 to 100
    message = Column(Text, nullable=True)  # Error message or description
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<Job id={self.id} status={self.status} progress={self.progress}>"
