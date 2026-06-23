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


class DocumentUpdateRequest(BaseModel):
    original_filename: str


class ContentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    user_id: UUID
    topic_id: UUID
    chunk_text: str
    chunk_index: int

    model_config = ConfigDict(from_attributes=True)


class ChunkUpdateRequest(BaseModel):
    chunk_text: str
