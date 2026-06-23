import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Document(Base):
    """
    SQLAlchemy model representing the documents table.
    Tracks metadata and ingestion state for user upload files.
    """

    __tablename__ = "documents"

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
    source_type = Column(
        String, nullable=False
    )  # e.g., 'upload_pdf', 'upload_text', 'manual_topic_text', 'web_scan'
    storage_path = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)
    status = Column(
        String, default="pending", nullable=False
    )  # e.g., 'pending', 'parsing', 'parsed', 'failed'
    ingested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Composite Index for isolation-safe queries
    __table_args__ = (Index("idx_documents_user_topic", "user_id", "topic_id"),)

    # Relationships
    user = relationship("User")
    topic = relationship("Topic", back_populates="documents")
    content_chunks = relationship(
        "ContentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document filename={self.original_filename} status={self.status}>"
