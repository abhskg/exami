"""
exams.py — Phase 6 Exam Engine & Simulation Router

POST /api/exams/sessions                 — Initialize timed or practice exam session
GET  /api/exams/sessions/{id}            — Get detailed status of exam session
POST /api/exams/sessions/{id}/submit-answer — Record answer submission and validate timed rules
POST /api/exams/sessions/{id}/complete       — Conclude exam session and compile results
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.api.auth_dependencies import get_current_user
from app.core.database import get_db
from app.models.exam import ExamResponse, ExamSession
from app.models.question import Question, QuestionOption
from app.models.question_set import QuestionSet, QuestionSetItem
from app.models.topic import Topic
from app.models.user import User
from app.schemas.exam import (
    ExamQuestionOptionResponse,
    ExamQuestionResponse,
    ExamResponseCreate,
    ExamResponseStatus,
    ExamSessionCreate,
    ExamSessionResponse,
    ExamSessionResults,
    TagPerformance,
)

router = APIRouter(prefix="/exams", tags=["exams"])


def _complete_session_internal(session: ExamSession, db: Session) -> None:
    """Closes an active exam session, calculates scores and commits."""
    session.status = "completed"
    now = datetime.now(timezone.utc)

    if session.mode == "timed":
        started_utc = session.started_at.replace(tzinfo=timezone.utc)
        expected_end = started_utc + timedelta(seconds=session.time_limit_seconds)
        session.completed_at = expected_end if now > expected_end else now
    else:
        session.completed_at = now

    # Calculate overall score percentage
    correct_count = sum(1 for r in session.responses if r.is_correct)
    if session.question_count > 0:
        session.score = round((correct_count / session.question_count) * 100.0, 2)
    else:
        session.score = 0.0

    db.add(session)
    db.commit()
    logger.info(
        f"Exam session {session.id} concluded. Mode: {session.mode}, Score: {session.score}%, Correct: {correct_count}/{session.question_count}"
    )


def _build_session_response(session: ExamSession, db: Session) -> ExamSessionResponse:
    """Helper to convert ExamSession ORM to ExamSessionResponse Pydantic model."""
    # Retrieve pre-saved QuestionSet items sorted by position
    items = (
        db.query(QuestionSetItem)
        .filter(QuestionSetItem.question_set_id == session.question_set_id)
        .order_by(QuestionSetItem.position.asc())
        .all()
    )

    questions_out = []
    # Reveal correct answers if session is in practice mode OR completed
    reveal_answers = session.mode == "practice" or session.status == "completed"
    answered_question_ids = {r.question_id for r in session.responses}

    for item in items:
        q = item.question
        options = sorted(q.options, key=lambda o: o.option_order)
        options_out = [
            ExamQuestionOptionResponse(
                id=o.id, option_text=o.option_text, option_order=o.option_order
            )
            for o in options
        ]

        tags_list = [tag.name for tag in q.tags]

        # Reveal explanation only if session is completed OR in practice mode after answering
        reveal_q_explanation = (session.status == "completed") or (
            session.mode == "practice" and q.id in answered_question_ids
        )

        questions_out.append(
            ExamQuestionResponse(
                id=q.id,
                question_text=q.question_text,
                difficulty=q.difficulty,
                options=options_out,
                tags=tags_list,
                explanation=q.explanation if reveal_q_explanation else None,
            )
        )

    responses_out = []
    for r in session.responses:
        correct_opt_id = None
        if reveal_answers:
            correct_opt_id = next((o.id for o in r.question.options if o.is_correct), None)

        responses_out.append(
            ExamResponseStatus(
                question_id=r.question_id,
                selected_option_id=r.selected_option_id,
                is_correct=r.is_correct if reveal_answers else None,
                correct_option_id=correct_opt_id,
            )
        )

    # Cleanly unpack tag filter JSON structure
    tag_filter_list = session.tag_filter
    if isinstance(tag_filter_list, str):
        try:
            tag_filter_list = json.loads(tag_filter_list)
        except Exception:
            tag_filter_list = None

    return ExamSessionResponse(
        id=session.id,
        user_id=session.user_id,
        topic_id=session.topic_id,
        question_set_id=session.question_set_id,
        mode=session.mode,
        tag_filter=tag_filter_list,
        difficulty_filter=session.difficulty_filter,
        question_count=session.question_count,
        time_limit_seconds=session.time_limit_seconds,
        status=session.status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        score=session.score,
        questions=questions_out,
        responses=responses_out,
    )


# ---------------------------------------------------------------------------
# POST /api/exams/sessions
# ---------------------------------------------------------------------------
@router.post("/sessions", response_model=ExamSessionResponse, status_code=status.HTTP_201_CREATED)
def create_exam_session(
    payload: ExamSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Starts a newTimed or Practice exam session. Matches questions from question
    bank based on filters, saves locked order to a QuestionSet, and creates session.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) attempting to start exam session for topic {payload.topic_id}. Mode: {payload.mode}, Count: {payload.question_count}"
    )

    topic = (
        db.query(Topic)
        .filter(Topic.id == payload.topic_id, Topic.user_id == current_user.id)
        .first()
    )
    if not topic:
        logger.warning(
            f"Start exam session failed: Topic {payload.topic_id} not found or access denied for User {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found or access denied.",
        )

    # Query matching active questions
    query = db.query(Question).filter(
        Question.user_id == current_user.id,
        Question.topic_id == payload.topic_id,
        Question.is_active.is_(True),
    )

    if payload.difficulty_filter and payload.difficulty_filter.lower() != "mixed":
        query = query.filter(Question.difficulty == payload.difficulty_filter.lower())

    if payload.tag_filter:
        from app.models.tag import Tag

        tag_names = [t.strip().lower() for t in payload.tag_filter if t.strip()]
        if tag_names:
            query = query.filter(Question.tags.any(Tag.name.in_(tag_names)))

    questions = query.order_by(func.random()).limit(payload.question_count).all()

    if not questions:
        logger.warning(
            f"Start exam session failed: No questions found matching filters for topic {payload.topic_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No questions found matching the selected filters. Please generate questions first.",
        )

    # Set default time limits
    time_limit = payload.time_limit_seconds
    if payload.mode == "timed" and not time_limit:
        time_limit = len(questions) * 60

    # Persist the frozen set of questions in QuestionSet and QuestionSetItems
    qset = QuestionSet(
        user_id=current_user.id,
        topic_id=payload.topic_id,
        name=f"Exam Session Set - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        generation_scope={
            "mode": payload.mode,
            "difficulty_filter": payload.difficulty_filter,
            "tag_filter": payload.tag_filter,
            "question_count": len(questions),
        },
    )
    db.add(qset)
    db.flush()

    for idx, q in enumerate(questions):
        item = QuestionSetItem(question_set_id=qset.id, question_id=q.id, position=idx)
        db.add(item)

    # Create exam session
    session = ExamSession(
        user_id=current_user.id,
        topic_id=payload.topic_id,
        question_set_id=qset.id,
        mode=payload.mode,
        tag_filter=payload.tag_filter,
        difficulty_filter=payload.difficulty_filter,
        question_count=len(questions),
        time_limit_seconds=time_limit,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(
        f"Exam session {session.id} successfully created with {session.question_count} questions for User {current_user.id}"
    )
    return _build_session_response(session, db)


# ---------------------------------------------------------------------------
# GET /api/exams/sessions/{id}
# ---------------------------------------------------------------------------
@router.get("/sessions/{id}", response_model=ExamSessionResponse)
def get_exam_session(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches details for an existing exam session, checking timed limits."""
    logger.info(f"User {current_user.email} (ID: {current_user.id}) fetching exam session {id}")
    session = (
        db.query(ExamSession)
        .filter(ExamSession.id == id, ExamSession.user_id == current_user.id)
        .first()
    )
    if not session:
        logger.warning(
            f"Fetch exam session failed: Session {id} not found for User {current_user.id}"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found.")

    # Auto-conclude if timed limits have expired on read
    if session.status == "in_progress" and session.mode == "timed":
        now = datetime.now(timezone.utc)
        elapsed = (now - session.started_at.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed > (session.time_limit_seconds + 5):
            logger.info(f"Exam session {id} time limit exceeded. Auto-concluding session on fetch.")
            _complete_session_internal(session, db)
            db.refresh(session)

    return _build_session_response(session, db)


# ---------------------------------------------------------------------------
# POST /api/exams/sessions/{id}/submit-answer
# ---------------------------------------------------------------------------
@router.post("/sessions/{id}/submit-answer", response_model=ExamResponseStatus)
def submit_answer(
    id: UUID,
    payload: ExamResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logs an answer submission to the exam response history. Enforces session state,
    verifies if question is part of the session, and enforces server timed lock boundaries.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) submitting answer to question {payload.question_id} in session {id}"
    )

    session = (
        db.query(ExamSession)
        .filter(ExamSession.id == id, ExamSession.user_id == current_user.id)
        .first()
    )
    if not session:
        logger.warning(f"Submit answer failed: Session {id} not found for User {current_user.id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found.")

    # Block submissions on concluded tests
    if session.status != "in_progress":
        logger.warning(f"Submit answer failed: Session {id} is already completed/locked.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit answers. This session is already {session.status}.",
        )

    # Verify expiration boundaries
    if session.mode == "timed":
        now = datetime.now(timezone.utc)
        elapsed = (now - session.started_at.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed > (session.time_limit_seconds + 5):
            logger.info(
                f"Exam session {id} time limit exceeded during submit-answer. Auto-concluding session."
            )
            _complete_session_internal(session, db)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time limit exceeded. This exam session has been locked.",
            )

    # Verify question is associated with the active session
    item = (
        db.query(QuestionSetItem)
        .filter(
            QuestionSetItem.question_set_id == session.question_set_id,
            QuestionSetItem.question_id == payload.question_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is not part of this exam session.",
        )

    # Validate option mapping
    is_correct = False
    if payload.selected_option_id:
        option = (
            db.query(QuestionOption)
            .filter(
                QuestionOption.id == payload.selected_option_id,
                QuestionOption.question_id == payload.question_id,
            )
            .first()
        )
        if not option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected option is not valid for this question.",
            )
        is_correct = option.is_correct

    # Log/Upsert responses
    response = (
        db.query(ExamResponse)
        .filter(
            ExamResponse.exam_session_id == session.id,
            ExamResponse.question_id == payload.question_id,
        )
        .first()
    )

    if response:
        response.selected_option_id = payload.selected_option_id
        response.is_correct = is_correct
        response.time_taken_seconds = payload.time_taken_seconds
        response.answered_at = datetime.now(timezone.utc)
    else:
        response = ExamResponse(
            exam_session_id=session.id,
            question_id=payload.question_id,
            selected_option_id=payload.selected_option_id,
            is_correct=is_correct,
            time_taken_seconds=payload.time_taken_seconds,
            answered_at=datetime.now(timezone.utc),
        )
        db.add(response)

    db.commit()
    db.refresh(response)

    # Only output correctness flags immediately if in practice mode
    reveal = session.mode == "practice"
    correct_opt_id = None
    if reveal:
        correct_opt_id = next((o.id for o in item.question.options if o.is_correct), None)

    logger.info(
        f"Answer submitted successfully for question {payload.question_id} in session {id}. Selected Option: {payload.selected_option_id}, Correct: {is_correct}"
    )

    return ExamResponseStatus(
        question_id=response.question_id,
        selected_option_id=response.selected_option_id,
        is_correct=response.is_correct if reveal else None,
        correct_option_id=correct_opt_id,
    )


# ---------------------------------------------------------------------------
# POST /api/exams/sessions/{id}/complete
# ---------------------------------------------------------------------------
@router.post("/sessions/{id}/complete", response_model=ExamSessionResponse)
def complete_exam_session(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Closes an active exam session explicitly, computes scores and returns results."""
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) explicitly requested completion of exam session {id}"
    )
    session = (
        db.query(ExamSession)
        .filter(ExamSession.id == id, ExamSession.user_id == current_user.id)
        .first()
    )
    if not session:
        logger.warning(
            f"Complete exam session failed: Session {id} not found for User {current_user.id}"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found.")

    if session.status == "in_progress":
        _complete_session_internal(session, db)
        db.refresh(session)

    return _build_session_response(session, db)


# ---------------------------------------------------------------------------
# GET /api/exams/sessions/{id}/results
# ---------------------------------------------------------------------------
@router.get("/sessions/{id}/results", response_model=ExamSessionResults)
def get_exam_session_results(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes and returns the detailed performance analysis for a concluded session.
    Calculates overall stats and tag-specific metrics.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) fetching results for session {id}"
    )
    session = (
        db.query(ExamSession)
        .filter(ExamSession.id == id, ExamSession.user_id == current_user.id)
        .first()
    )

    if not session:
        logger.warning(f"Fetch results failed: Session {id} not found for User {current_user.id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found.")

    # Auto-conclude if timed limits have expired
    if session.status == "in_progress" and session.mode == "timed":
        now = datetime.now(timezone.utc)
        elapsed = (now - session.started_at.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed > (session.time_limit_seconds + 5):
            logger.info(
                f"Exam session {id} time limit exceeded. Auto-concluding session on results fetch."
            )
            _complete_session_internal(session, db)
            db.refresh(session)
        else:
            logger.warning(
                f"Fetch results failed: Attempted to get results for active timed session {id} before completion."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot retrieve results for an active timed session. Complete the session first.",
            )

    # Let's count correctness stats
    correct_count = sum(1 for r in session.responses if r.is_correct)

    # Identify which question IDs have been answered
    # Note that an answer might be logged but selected_option_id could be null (skipped)
    submitted_qids = {r.question_id for r in session.responses if r.selected_option_id is not None}
    incorrect_count = sum(
        1 for r in session.responses if not r.is_correct and r.selected_option_id is not None
    )

    # A question is skipped if it has no response logged, or if selected_option_id is None
    # Let's get the list of all questions in the set to account for untyped/unanswered ones
    items = (
        db.query(QuestionSetItem)
        .filter(QuestionSetItem.question_set_id == session.question_set_id)
        .all()
    )

    total_q_count = len(items)
    # Double check if total_q_count matches session.question_count
    if total_q_count == 0:
        total_q_count = session.question_count

    skipped_count = total_q_count - len(submitted_qids)

    # Compute speeds
    total_time_taken = sum(r.time_taken_seconds or 0 for r in session.responses)
    # Average speed is total time taken / count of answered questions
    answered_count = len(submitted_qids)
    avg_time_taken = (total_time_taken / answered_count) if answered_count > 0 else 0.0

    # Calculate overall score percentage if not already completed/calculated
    score = session.score
    if score is None:
        if total_q_count > 0:
            score = round((correct_count / total_q_count) * 100.0, 2)
        else:
            score = 0.0

    # Compile tag performance
    response_by_qid = {r.question_id: r for r in session.responses}

    tag_stats = {}  # tag_name -> {total, correct, incorrect, skipped}
    for item in items:
        q = item.question
        resp = response_by_qid.get(q.id)

        is_q_correct = resp.is_correct if resp else False
        is_q_submitted = (resp.selected_option_id is not None) if resp else False

        for tag in q.tags:
            tag_name_lower = tag.name.strip().lower()
            if tag_name_lower not in tag_stats:
                tag_stats[tag_name_lower] = {
                    "tag_name": tag.name,
                    "total": 0,
                    "correct": 0,
                    "incorrect": 0,
                    "skipped": 0,
                }

            tag_stats[tag_name_lower]["total"] += 1
            if is_q_submitted:
                if is_q_correct:
                    tag_stats[tag_name_lower]["correct"] += 1
                else:
                    tag_stats[tag_name_lower]["incorrect"] += 1
            else:
                tag_stats[tag_name_lower]["skipped"] += 1

    tag_performance_list = []
    for t_lower, stats in tag_stats.items():
        total_tag_q = stats["total"]
        pct = round((stats["correct"] / total_tag_q) * 100.0, 2) if total_tag_q > 0 else 0.0
        tag_performance_list.append(
            TagPerformance(
                tag_name=stats["tag_name"],
                total_questions=total_tag_q,
                correct_count=stats["correct"],
                incorrect_count=stats["incorrect"],
                skipped_count=stats["skipped"],
                percentage=pct,
            )
        )

    # Sort tag performance list alphabetically by tag name for UI consistency
    tag_performance_list.sort(key=lambda tp: tp.tag_name.lower())

    return ExamSessionResults(
        session_id=session.id,
        mode=session.mode,
        status=session.status,
        score=score,
        question_count=total_q_count,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        skipped_count=skipped_count,
        total_time_taken_seconds=total_time_taken,
        average_time_taken_seconds=round(avg_time_taken, 2),
        tag_performance=tag_performance_list,
    )
