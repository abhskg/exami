from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ExamQuestionOptionResponse(BaseModel):
    """Option details for a question inside an exam session."""
    id: UUID
    option_text: str
    option_order: int

    model_config = ConfigDict(from_attributes=True)


class ExamQuestionResponse(BaseModel):
    """Question details for an exam session, hiding correctness attributes."""
    id: UUID
    question_text: str
    difficulty: str
    options: list[ExamQuestionOptionResponse] = []
    tags: list[str] = []
    explanation: Optional[str] = None  # Revealed only when session is completed or in practice mode

    model_config = ConfigDict(from_attributes=True)


class ExamSessionCreate(BaseModel):
    """Payload to initialize a timed or practice exam session."""
    topic_id: UUID
    mode: str = Field(..., pattern="^(practice|timed)$", description="Mode: 'practice' or 'timed'.")
    difficulty_filter: Optional[str] = Field(
        default=None,
        pattern="^(easy|medium|hard|mixed)$",
        description="Filter difficulty level: easy, medium, hard, mixed.",
    )
    tag_filter: Optional[list[str]] = Field(
        default=None,
        description="Optional concept tags to scope exam questions.",
    )
    question_count: int = Field(default=10, ge=1, le=100, description="Target number of questions (1-100).")
    time_limit_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        description="Time limit in seconds. If omitted in timed mode, defaults to 60s per question.",
    )


class ExamResponseCreate(BaseModel):
    """Payload for submitting or modifying an answer to a question in a session."""
    question_id: UUID
    selected_option_id: Optional[UUID] = None
    time_taken_seconds: Optional[int] = None


class ExamResponseStatus(BaseModel):
    """Status details for a recorded user response."""
    question_id: UUID
    selected_option_id: Optional[UUID] = None
    is_correct: Optional[bool] = None  # Revealed only when session is completed or in practice mode
    correct_option_id: Optional[UUID] = None  # Revealed only when session is completed or in practice mode

    model_config = ConfigDict(from_attributes=True)


class ExamSessionResponse(BaseModel):
    """State snapshot of an active or completed exam session."""
    id: UUID
    user_id: UUID
    topic_id: UUID
    question_set_id: Optional[UUID] = None
    mode: str
    tag_filter: Optional[list[str]] = None
    difficulty_filter: Optional[str] = None
    question_count: int
    time_limit_seconds: Optional[int] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    score: Optional[float] = None
    questions: list[ExamQuestionResponse] = []
    responses: list[ExamResponseStatus] = []

    model_config = ConfigDict(from_attributes=True)
