import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class User(Base):
    """
    SQLAlchemy model representing the users table.
    Enforces user isolation, with other database objects linking to users.id.
    """
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        nullable=False
    )
    email = Column(
        String, 
        unique=True, 
        index=True, 
        nullable=False
    )
    password_hash = Column(
        String, 
        nullable=False
    )
    display_name = Column(
        String, 
        nullable=True
    )
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    plan_tier = Column(
        String, 
        default="free", 
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<User email={self.email} plan={self.plan_tier}>"
