from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class ConceptNode(BaseModel):
    id: str
    title: str
    description: str
    tags: List[str]
    path: str


class ConceptEdge(BaseModel):
    source: str
    target: str


class KnowledgeGraph(BaseModel):
    nodes: List[ConceptNode]
    edges: List[ConceptEdge]


class ConceptReviewRequest(BaseModel):
    job_id: UUID
    document_id: UUID
    approved_concepts: List[dict]


class DeepenRequest(BaseModel):
    mode: str  # "merge" or "new"
    new_raw_data: str
