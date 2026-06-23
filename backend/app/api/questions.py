"""
questions.py — Phase 5 Question Bank API Router

POST /api/questions/generate   — Generate MCQs from topic context via Gemini
GET  /api/questions/           — List saved questions for a topic
GET  /api/questions/tags       — List all tags for a topic (for UI chips)
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.core.database import get_db
from app.models.question import Question, QuestionOption, question_tags
from app.models.tag import Tag
from app.models.topic import Topic
from app.models.user import User
from app.schemas.question import (
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    QuestionAnalyticsResponse,
    QuestionOptionUpdateRequest,
    QuestionResponse,
    QuestionUpdateRequest,
    TagAnalytics,
    TagResponse,
    TagUpdateRequest,
    TopicAnalytics,
)
from app.services import question_bank

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["questions"])


# ---------------------------------------------------------------------------
# POST /api/questions/generate
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=GenerateQuestionsResponse,
    status_code=status.HTTP_200_OK,
)
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
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) requesting question generation. Topic: {payload.topic_id}, Count: {payload.count}, Difficulty: {payload.difficulty}, Tags: {payload.tag_filters}"
    )

    # Enforce topic ownership
    topic = (
        db.query(Topic)
        .filter(
            Topic.id == payload.topic_id,
            Topic.user_id == current_user.id,
        )
        .first()
    )
    if not topic:
        logger.warning(
            f"Generate questions failed: Topic {payload.topic_id} not found or access denied for User {current_user.id}"
        )
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
        logger.error(
            f"Question generation failed for User {current_user.id}, Topic {payload.topic_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {str(e)}",
        )

    questions_out = [QuestionResponse.from_orm_with_tags(q) for q in saved]
    logger.info(
        f"Successfully generated and saved {len(questions_out)} questions for Topic {payload.topic_id} and User {current_user.id}"
    )
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
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) listing questions for topic {topic_id}. Filters: difficulty={difficulty}, tag={tag}, limit={limit}"
    )

    # Enforce topic ownership
    topic = (
        db.query(Topic)
        .filter(
            Topic.id == topic_id,
            Topic.user_id == current_user.id,
        )
        .first()
    )
    if not topic:
        logger.warning(
            f"List questions failed: Topic {topic_id} not found or access denied for User {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found.",
        )

    query = db.query(Question).filter(
        Question.user_id == current_user.id,
        Question.topic_id == topic_id,
        Question.is_active.is_(True),
    )

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    if tag:
        from app.models.question import question_tags as qt
        from app.models.tag import Tag

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
            logger.debug(f"Tag '{tag}' not found for topic {topic_id}. Returning empty list.")
            return []

    questions = query.order_by(Question.created_at.desc()).limit(limit).all()
    logger.debug(f"Retrieved {len(questions)} questions for topic {topic_id}")
    return [QuestionResponse.from_orm_with_tags(q) for q in questions]


# ---------------------------------------------------------------------------
# GET /api/questions/analytics
# ---------------------------------------------------------------------------


@router.get("/analytics", response_model=QuestionAnalyticsResponse)
def get_question_analytics(
    topic_id: Optional[UUID] = Query(None, description="Optional topic UUID to get analytics for."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get broad level analytics for the user's questions.
    If topic_id is provided, returns specific topic stats (total, difficulty breakdown, tag breakdown).
    Also returns a topic-wide question count breakdown across all of the user's topics.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) requesting question analytics. topic_id={topic_id}"
    )

    # 1. Base filter for active questions owned by the user
    base_filter = [
        Question.user_id == current_user.id,
        Question.is_active.is_(True),
    ]

    # If topic_id is specified, verify ownership and filter stats
    if topic_id:
        topic = (
            db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == current_user.id).first()
        )
        if not topic:
            logger.warning(
                f"Analytics failed: Topic {topic_id} not found or access denied for User {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found or access denied.",
            )
        # Add topic_id to filters for topic-specific calculations
        topic_filters = base_filter + [Question.topic_id == topic_id]
    else:
        topic_filters = base_filter

    # 2. Total active questions count
    total_questions = db.query(Question).filter(*topic_filters).count()

    # 3. Difficulty breakdown (initialize with 0s)
    difficulty_breakdown = {"easy": 0, "medium": 0, "hard": 0}
    difficulty_stats = (
        db.query(Question.difficulty, func.count(Question.id))
        .filter(*topic_filters)
        .group_by(Question.difficulty)
        .all()
    )
    for diff, count in difficulty_stats:
        if diff in difficulty_breakdown:
            difficulty_breakdown[diff] = count

    # 4. Tag breakdown
    tag_stats = (
        db.query(Tag.name, func.count(Question.id))
        .join(question_tags, Tag.id == question_tags.c.tag_id)
        .join(Question, Question.id == question_tags.c.question_id)
        .filter(*topic_filters)
        .group_by(Tag.name)
        .order_by(func.count(Question.id).desc())
        .all()
    )
    tag_breakdown = [TagAnalytics(tag_name=name, question_count=count) for name, count in tag_stats]

    # 5. Overall topic breakdown (always across all topics of the user)
    # Use outerjoin to include topics that have 0 questions
    topic_stats = (
        db.query(Topic.name, func.count(Question.id))
        .outerjoin(Question, (Topic.id == Question.topic_id) & (Question.is_active.is_(True)))
        .filter(Topic.user_id == current_user.id)
        .group_by(Topic.name)
        .order_by(func.count(Question.id).desc())
        .all()
    )
    topic_breakdown = [
        TopicAnalytics(topic_name=name, question_count=count) for name, count in topic_stats
    ]

    return QuestionAnalyticsResponse(
        total_questions=total_questions,
        difficulty_breakdown=difficulty_breakdown,
        tag_breakdown=tag_breakdown,
        topic_breakdown=topic_breakdown,
    )


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
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) listing tags for topic {topic_id}"
    )
    topic = (
        db.query(Topic)
        .filter(
            Topic.id == topic_id,
            Topic.user_id == current_user.id,
        )
        .first()
    )
    if not topic:
        logger.warning(
            f"List tags failed: Topic {topic_id} not found or access denied for User {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found.",
        )

    tags = question_bank.list_topic_tags(
        topic_id=topic_id,
        user_id=current_user.id,
        db=db,
    )
    logger.debug(f"Retrieved {len(tags)} tags for topic {topic_id}")
    return tags


@router.put("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: UUID,
    payload: QuestionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a question, its options, and tags.
    """
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.user_id == current_user.id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    question.question_text = payload.question_text
    question.explanation = payload.explanation
    question.difficulty = payload.difficulty

    # Update Options
    for opt in question.options:
        db.delete(opt)

    for idx, opt_in in enumerate(payload.options[:4]):
        option = QuestionOption(
            question_id=question.id,
            option_text=opt_in.option_text,
            is_correct=opt_in.is_correct,
            option_order=idx,
        )
        db.add(option)

    # Update tags association
    db.execute(question_tags.delete().where(question_tags.c.question_id == question.id))

    from app.services.question_bank import _resolve_or_create_tag

    for tag_name in payload.tags:
        t_name = tag_name.strip().lower()
        if not t_name:
            continue
        tag = _resolve_or_create_tag(t_name, question.topic_id, current_user.id, db)

        exists = db.execute(
            text("SELECT 1 FROM question_tags WHERE question_id = :qid AND tag_id = :tid"),
            {"qid": question.id, "tid": tag.id},
        ).first()
        if not exists:
            db.execute(question_tags.insert().values(question_id=question.id, tag_id=tag.id))

    db.commit()
    db.refresh(question)

    return QuestionResponse.from_orm_with_tags(question)


@router.delete("/{question_id}", status_code=status.HTTP_200_OK)
def delete_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Physically delete a question from the database.
    """
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.user_id == current_user.id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    db.delete(question)
    db.commit()
    logger.info(f"User {current_user.email} deleted question {question_id}")
    return {"message": "Question deleted successfully."}


@router.put("/tags/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: UUID,
    payload: TagUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rename a tag across all questions inside a topic. Handles merges if target tag already exists.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")

    new_name = payload.name.strip().lower()
    if not new_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tag name cannot be empty."
        )

    existing_tag = (
        db.query(Tag)
        .filter(
            Tag.user_id == current_user.id,
            Tag.topic_id == tag.topic_id,
            Tag.name == new_name,
            Tag.id != tag_id,
        )
        .first()
    )

    if existing_tag:
        links = db.execute(
            text("SELECT question_id FROM question_tags WHERE tag_id = :tid"), {"tid": tag.id}
        ).all()

        for link in links:
            qid = link[0]
            already_linked = db.execute(
                text("SELECT 1 FROM question_tags WHERE question_id = :qid AND tag_id = :tid"),
                {"qid": qid, "tid": existing_tag.id},
            ).first()
            if not already_linked:
                db.execute(question_tags.insert().values(question_id=qid, tag_id=existing_tag.id))

        db.delete(tag)
        db.commit()
        logger.info(
            f"User {current_user.email} merged tag {tag_id} into existing tag {existing_tag.id} ('{new_name}')"
        )
        return existing_tag

    tag.name = new_name
    db.commit()
    db.refresh(tag)
    logger.info(f"User {current_user.email} renamed tag {tag_id} to '{new_name}'")
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_200_OK)
def delete_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a tag from the database.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")

    db.delete(tag)
    db.commit()
    logger.info(
        f"User {current_user.email} deleted tag {tag_id} and removed it from all questions."
    )
    return {"message": "Tag deleted successfully."}
