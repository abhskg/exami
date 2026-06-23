from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class GenerateQuestionsRequest(BaseModel):
    """Payload for POST /api/questions/generate."""

    topic_id: UUID
    count: int = Field(
        default=5, ge=1, le=50, description="Number of questions to generate (1–50)."
    )
    difficulty: str = Field(
        default="medium",
        pattern="^(easy|medium|hard|mixed)$",
        description="Target difficulty level: easy, medium, hard, or mixed.",
    )
    tag_filters: list[str] = Field(
        default_factory=list,
        description="Optional list of concept tags to focus the generation context.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class QuestionOptionResponse(BaseModel):
    id: UUID
    option_text: str
    is_correct: bool
    option_order: int

    model_config = ConfigDict(from_attributes=True)


class QuestionResponse(BaseModel):
    id: UUID
    user_id: UUID
    topic_id: UUID
    question_text: str
    explanation: Optional[str] = None
    difficulty: str
    generated_by: str
    is_active: bool
    created_at: datetime
    options: list[QuestionOptionResponse] = []
    tags: list[str] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_tags(cls, question) -> "QuestionResponse":
        """
        Build response from an ORM Question object, resolving the many-to-many
        Tag relationship into plain strings.  We build via a plain dict so that
        Pydantic never tries to coerce ORM Tag objects into strings directly.
        """
        resolved_tags = [tag.name for tag in question.tags]
        resolved_options = [QuestionOptionResponse.model_validate(opt) for opt in question.options]
        return cls(
            id=question.id,
            user_id=question.user_id,
            topic_id=question.topic_id,
            question_text=question.question_text,
            explanation=question.explanation,
            difficulty=question.difficulty,
            generated_by=question.generated_by,
            is_active=question.is_active,
            created_at=question.created_at,
            options=resolved_options,
            tags=resolved_tags,
        )


class TagResponse(BaseModel):
    id: UUID
    name: str
    topic_id: UUID

    model_config = ConfigDict(from_attributes=True)


class GenerateQuestionsResponse(BaseModel):
    generated: int
    questions: list[QuestionResponse]


class TagUpdateRequest(BaseModel):
    name: str


class QuestionOptionUpdateRequest(BaseModel):
    id: Optional[UUID] = None
    option_text: str
    is_correct: bool
    option_order: int


class QuestionUpdateRequest(BaseModel):
    question_text: str
    explanation: Optional[str] = None
    difficulty: str
    tags: list[str]
    options: list[QuestionOptionUpdateRequest]

