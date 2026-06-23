from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: UUID
    user_id: UUID
    topic_id: UUID
    source_type: str
    storage_path: Optional[str] = None
    original_filename: Optional[str] = None
    status: str
    ingested_at: datetime

    model_config = ConfigDict(from_attributes=True)
