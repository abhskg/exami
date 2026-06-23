"""
question_bank.py — Phase 5 Question Bank Service

Task 5.1: Vector Similarity Query Function
    get_similar_chunks() — embeds a query string via Gemini, runs a pgvector
    cosine-distance search on content_chunks, filtered by user_id + topic_id.

Task 5.2: Structured MCQ Generation Service
    generate_questions() — assembles context from similar chunks, calls Gemini
    with a structured JSON output schema, persists Question / QuestionOption /
    Tag rows inside a single DB transaction, and returns the saved objects.
"""

import json
import logging
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content_chunk import ContentChunk
from app.models.question import Question, QuestionOption, question_tags
from app.models.tag import Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _embed_query(query_text: str) -> list[float]:
    """
    Embed a single query string using centralized llm_service.
    """
    from app.services import llm_service

    embs = llm_service.embed_text([query_text])
    return embs[0]


def _call_llm_generate(prompt: str, count: int, difficulty: str) -> list[dict]:
    """
    Call centralized llm_service to generate MCQs.
    """
    from app.services import llm_service

    return llm_service.generate_mcqs(prompt, count, difficulty)


# ---------------------------------------------------------------------------
# Task 5.1 — Vector Similarity Query
# ---------------------------------------------------------------------------


def get_similar_chunks(
    query_text: str,
    topic_id: UUID,
    user_id: UUID,
    k: int = 10,
    db: Session = None,
) -> list[ContentChunk]:
    """
    Embed *query_text* and retrieve the top-*k* content_chunks for a given
    topic/user ordered by cosine distance (closest first).

    Uses pgvector's `<=>` operator which computes cosine distance between two
    half-precision or full-precision vectors.  The query is strictly scoped to
    the provided user_id and topic_id to enforce row-level isolation.
    """
    if db is None:
        raise ValueError("A database session is required.")

    query_vector = _embed_query(query_text)

    # Cast vector literal to the correct pgvector type so SQLAlchemy passes it cleanly.
    vector_literal = f"[{','.join(str(v) for v in query_vector)}]"

    results = (
        db.query(ContentChunk)
        .filter(
            ContentChunk.user_id == user_id,
            ContentChunk.topic_id == topic_id,
            ContentChunk.embedding.isnot(None),
        )
        .order_by(
            # cosine distance ascending = most similar first
            ContentChunk.embedding.op("<=>")(text(f"'{vector_literal}'::vector"))
        )
        .limit(k)
        .all()
    )

    return results


# ---------------------------------------------------------------------------
# Task 5.2 — Structured MCQ Generation
# ---------------------------------------------------------------------------


def _resolve_or_create_tag(
    name: str,
    topic_id: UUID,
    user_id: UUID,
    db: Session,
) -> Tag:
    """
    Return an existing Tag matching (user_id, topic_id, name) or create one.
    The unique constraint uq_tag_user_topic_name is respected via a SELECT-first
    strategy to avoid duplicate key violations inside the transaction.
    """
    tag = (
        db.query(Tag)
        .filter(
            Tag.user_id == user_id,
            Tag.topic_id == topic_id,
            Tag.name == name.strip().lower(),
        )
        .first()
    )
    if tag is None:
        tag = Tag(
            user_id=user_id,
            topic_id=topic_id,
            name=name.strip().lower(),
            created_by="ai_generated",
        )
        db.add(tag)
        db.flush()  # obtain the PK without committing the outer transaction
    return tag


def generate_questions(
    topic_id: UUID,
    user_id: UUID,
    count: int,
    difficulty: str,
    tag_filters: list[str],
    db: Session,
) -> list[Question]:
    """
    End-to-end MCQ generation pipeline:

    1. Determine a search query from tag_filters (or use a generic topic prompt).
    2. Retrieve top-k similar content chunks via vector similarity.
    3. Build a structured Gemini prompt.
    4. Call Gemini and parse the JSON array of MCQs.
    5. Persist Question, QuestionOption, and Tag rows in a single transaction.
    6. Return the list of saved Question objects.
    """
    # --- Step 1: Assemble search query ----------------------------------------
    if tag_filters:
        query_text = " ".join(tag_filters)
    else:
        query_text = "key concepts principles definitions theory"

    # --- Step 2: Fetch relevant context chunks --------------------------------
    chunks = get_similar_chunks(
        query_text=query_text,
        topic_id=topic_id,
        user_id=user_id,
        k=min(count * 2, 20),
        db=db,
    )

    context_blocks = "\n\n---\n\n".join(c.chunk_text for c in chunks)
    if not context_blocks.strip():
        context_blocks = "(No document context available — generate general questions)"

    # --- Step 3 & 4: Call LLM in batches of at most 5 questions ----------------
    import random
    import time

    batch_size = 5
    raw_mcqs = []
    remaining = count
    batch_num = 1
    last_exception = None

    while remaining > 0:
        current_batch_size = min(remaining, batch_size)

        tag_hint = (
            f"Focus especially on these concepts/tags: {', '.join(tag_filters)}."
            if tag_filters
            else "Cover a broad range of key concepts from the context."
        )

        difficulty_instruction = {
            "easy": "Make questions straightforward and fact-based.",
            "medium": "Make questions moderately challenging requiring some reasoning.",
            "hard": "Make questions challenging, requiring deep understanding and analysis.",
            "mixed": "Mix easy, medium, and hard difficulty levels across questions.",
        }.get(difficulty, "Make questions moderately challenging.")

        prompt = f"""You are an expert exam question generator and educator. Generate exactly {current_batch_size} high-quality multiple-choice questions (MCQs) based on the study material provided below.

CONTEXT (study material excerpts):
{context_blocks}

REQUIREMENTS:
- Generate exactly {current_batch_size} MCQs.
- Each question must have exactly 4 answer options.
- Exactly one option must be correct (is_correct: true).
- {difficulty_instruction}
- {tag_hint}
- For the "explanation" field, write a DETAILED and ELABORATE explanation (minimum 4–6 sentences) that:
    1. Clearly states WHY the correct answer is right, referencing specific concepts from the study material.
    2. Explains WHY each of the incorrect options (distractors) is wrong — pointing out the common misconception each distractor targets.
    3. Provides a concrete real-world example, analogy, or reference to reinforce understanding.
    4. Mentions any relevant formula, definition, or rule that applies.
    The explanation must be educational and thorough — a student reading it should gain a deep understanding of the topic, not just know which answer to pick.
- Suggest 1–3 relevant topic tags (short lowercase strings, e.g. "recursion", "sorting").

OUTPUT FORMAT (strict JSON array — no markdown fences, no extra text):
[
  {{
    "question_text": "...",
    "options": [
      {{"text": "...", "is_correct": true}},
      {{"text": "...", "is_correct": false}},
      {{"text": "...", "is_correct": false}},
      {{"text": "...", "is_correct": false}}
    ],
    "explanation": "A detailed multi-sentence explanation covering why the correct answer is right, why each wrong option is incorrect (addressing common misconceptions), and a real-world example or analogy to solidify understanding.",
    "tags": ["tag1", "tag2"],
    "difficulty": "{difficulty if difficulty != 'mixed' else 'medium'}"
  }}
]"""

        logger.info(
            f"Generating batch {batch_num} with {current_batch_size} questions (remaining: {remaining - current_batch_size})."
        )
        try:
            batch_res = _call_llm_generate(prompt, current_batch_size, difficulty)
            if batch_res:
                raw_mcqs.extend(batch_res)
        except Exception as e:
            logger.error(f"Error in batch {batch_num} question generation: {e}")
            last_exception = e

        remaining -= current_batch_size
        batch_num += 1

        if remaining > 0:
            time.sleep(1.0)

    if not raw_mcqs and last_exception:
        # If we got absolutely no questions across all batches, raise the exception
        logger.error("No questions generated and API failed on last batch.")
        raise last_exception

    # --- Step 5: Persist to DB ------------------------------------------------
    saved_questions: list[Question] = []

    for raw in raw_mcqs:
        try:
            # Validate minimum structure
            q_text = raw.get("question_text", "").strip()
            options_raw = raw.get("options", [])
            if not q_text or not options_raw:
                logger.warning(
                    "Skipping malformed MCQ from Gemini response (missing text or options)."
                )
                continue

            q_difficulty = raw.get("difficulty", difficulty if difficulty != "mixed" else "medium")
            q_explanation = raw.get("explanation", "")
            q_tags = [t.strip().lower() for t in raw.get("tags", []) if t.strip()]

            # Find source chunk (use first chunk as attribution if available)
            source_chunk_id: Optional[UUID] = chunks[0].id if chunks else None

            question = Question(
                user_id=user_id,
                topic_id=topic_id,
                source_chunk_id=source_chunk_id,
                question_text=q_text,
                explanation=q_explanation,
                difficulty=q_difficulty,
                generated_by="ai",
                is_active=True,
            )
            db.add(question)
            db.flush()  # get question.id

            # Shuffling option positions to randomize correct option
            options_list = list(options_raw[:4])
            random.shuffle(options_list)

            # Options persistence
            for order_idx, opt in enumerate(options_list):
                opt_text = ""
                opt_is_correct = False
                if isinstance(opt, dict):
                    opt_text = opt.get("text", "").strip()
                    opt_is_correct = bool(opt.get("is_correct", False))
                elif isinstance(opt, str):
                    opt_text = opt.strip()
                    opt_is_correct = False

                option = QuestionOption(
                    question_id=question.id,
                    option_text=opt_text,
                    is_correct=opt_is_correct,
                    option_order=order_idx,
                )
                db.add(option)

            # Tags (many-to-many via question_tags association table)
            for tag_name in q_tags:
                if not tag_name:
                    continue
                tag = _resolve_or_create_tag(tag_name, topic_id, user_id, db)
                # Insert into association table only if not already linked
                exists = db.execute(
                    text("SELECT 1 FROM question_tags WHERE question_id = :qid AND tag_id = :tid"),
                    {"qid": question.id, "tid": tag.id},
                ).first()
                if not exists:
                    db.execute(
                        question_tags.insert().values(question_id=question.id, tag_id=tag.id)
                    )

            db.flush()
            saved_questions.append(question)
        except Exception as q_err:
            logger.error(f"Error parsing/saving single generated question: {q_err}")
            continue

    db.commit()

    # Refresh to load relationships
    for q in saved_questions:
        db.refresh(q)

    logger.info(
        f"Generated and saved {len(saved_questions)} questions for topic={topic_id}, user={user_id}."
    )
    return saved_questions


# ---------------------------------------------------------------------------
# Tag listing helper (used by the frontend to populate tag filter chips)
# ---------------------------------------------------------------------------


def list_topic_tags(topic_id: UUID, user_id: UUID, db: Session) -> list[Tag]:
    """Return all tags belonging to a user's topic, ordered alphabetically."""
    return (
        db.query(Tag)
        .filter(Tag.user_id == user_id, Tag.topic_id == topic_id)
        .order_by(Tag.name)
        .all()
    )
