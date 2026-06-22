"""
questions.py — Phase 5 Question Bank API Router

POST /api/questions/generate   — Generate MCQs from topic context via Gemini
GET  /api/questions/           — List saved questions for a topic
GET  /api/questions/tags       — List all tags for a topic (for UI chips)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.topic import Topic
from app.models.question import Question
from app.schemas.question import (
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    QuestionResponse,
    TagResponse,
)
from app.services import question_bank

router = APIRouter(prefix="/questions", tags=["questions"])


# ---------------------------------------------------------------------------
# POST /api/questions/generate
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=GenerateQuestionsResponse, status_code=status.HTTP_200_OK)
def generate_questions(
    payload: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate MCQs for a given topic using Gemini AI.
    Context chunks are retrieved via pgvector similarity search, then Gemini
    is prompted to produce structured JSON MCQs which are persisted to the DB.
    """
    # Enforce topic ownership
    topic = db.query(Topic).filter(
        Topic.id == payload.topic_id,
        Topic.user_id == current_user.id,
    ).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found or access denied.",
        )

    try:
        saved = question_bank.generate_questions(
            topic_id=payload.topic_id,
            user_id=current_user.id,
            count=payload.count,
            difficulty=payload.difficulty,
            tag_filters=payload.tag_filters,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {str(e)}",
        )

    questions_out = [QuestionResponse.from_orm_with_tags(q) for q in saved]
    return GenerateQuestionsResponse(generated=len(questions_out), questions=questions_out)


# ---------------------------------------------------------------------------
# GET /api/questions/
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[QuestionResponse])
def list_questions(
    topic_id: UUID = Query(..., description="Filter questions by topic UUID."),
    difficulty: str = Query(None, description="Filter by difficulty: easy, medium, hard."),
    tag: str = Query(None, description="Filter by tag name (exact, case-insensitive)."),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all questions for the authenticated user within a specific topic.
    Supports optional filtering by difficulty and tag name.
    """
    # Enforce topic ownership
    topic = db.query(Topic).filter(
        Topic.id == topic_id,
        Topic.user_id == current_user.id,
    ).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found.",
        )

    query = (
        db.query(Question)
        .filter(
            Question.user_id == current_user.id,
            Question.topic_id == topic_id,
            Question.is_active.is_(True),
        )
    )

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    if tag:
        from app.models.tag import Tag
        from app.models.question import question_tags as qt
        tag_obj = (
            db.query(Tag)
            .filter(
                Tag.user_id == current_user.id,
                Tag.topic_id == topic_id,
                Tag.name == tag.strip().lower(),
            )
            .first()
        )
        if tag_obj:
            query = query.join(qt, Question.id == qt.c.question_id).filter(
                qt.c.tag_id == tag_obj.id
            )
        else:
            return []

    questions = query.order_by(Question.created_at.desc()).limit(limit).all()
    return [QuestionResponse.from_orm_with_tags(q) for q in questions]


# ---------------------------------------------------------------------------
# GET /api/questions/tags
# ---------------------------------------------------------------------------

@router.get("/tags", response_model=list[TagResponse])
def list_tags(
    topic_id: UUID = Query(..., description="Topic UUID to list tags for."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all tags associated with the user's topic, ordered alphabetically.
    Used by the frontend to populate tag-filter chip selectors.
    """
    topic = db.query(Topic).filter(
        Topic.id == topic_id,
        Topic.user_id == current_user.id,
    ).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found.",
        )

    tags = question_bank.list_topic_tags(
        topic_id=topic_id,
        user_id=current_user.id,
        db=db,
    )
    return tags
