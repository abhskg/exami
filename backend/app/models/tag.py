import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Tag(Base):
    """
    SQLAlchemy model representing the tags table.
    Provides conceptual taxonomy tags, scoped per user/topic to avoid conflicts.
    """
    __tablename__ = "tags"

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
    name = Column(
        String, 
        nullable=False
    )
    parent_tag_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("tags.id", ondelete="SET NULL"), 
        nullable=True
    )
    created_by = Column(
        String, 
        default="ai_generated", 
        nullable=False
    )  # e.g., 'ai_generated', 'user_defined'
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Unique constraint on (user_id, topic_id, name)
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", "name", name="uq_tag_user_topic_name"),
        Index("idx_tags_user_topic", "user_id", "topic_id"),
    )

    # Relationships
    user = relationship("User")
    topic = relationship("Topic", back_populates="tags")
    parent_tag = relationship("Tag", remote_side=[id], back_populates="sub_tags")
    sub_tags = relationship("Tag", back_populates="parent_tag", cascade="all, delete-orphan")
    
    # Many-to-many relationship with Question (resolved dynamically via name string)
    questions = relationship("Question", secondary="question_tags", back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag name={self.name} topic_id={self.topic_id}>"
