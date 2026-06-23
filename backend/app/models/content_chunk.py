import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.config import settings
from app.core.database import Base


class ContentChunk(Base):
    """
    SQLAlchemy model representing the content_chunks table.
    Stores partitioned texts and their respective pgvector embedding vectors.
    """

    __tablename__ = "content_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    chunk_text = Column(Text, nullable=False)
    # Embedding vector dimension dynamically resolved from config settings
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    chunk_index = Column(Integer, nullable=False)

    # Index for user isolation scoping
    __table_args__ = (Index("idx_content_chunks_user_topic", "user_id", "topic_id"),)

    # Relationships
    document = relationship("Document", back_populates="content_chunks")
    user = relationship("User")
    topic = relationship("Topic")
    questions = relationship("Question", back_populates="source_chunk")

    def __repr__(self) -> str:
        return (
            f"<ContentChunk id={self.id} document_id={self.document_id} index={self.chunk_index}>"
        )
