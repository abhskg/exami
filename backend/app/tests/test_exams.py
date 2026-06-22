"""
test_exams.py — Phase 6 Integration Tests

Covers:
- Task 6.1: POST /api/exams/sessions creates sessions, locks question order
- Task 6.2: POST /api/exams/sessions/{id}/submit-answer logs answers, checks timeouts
- Security checks: hides correctness in timed sessions, exposes in practice
- Completion checks: score calculation accuracy
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.models.user import User
from app.models.topic import Topic
from app.models.question import Question, QuestionOption
from app.models.exam import ExamSession, ExamResponse
from app.core.security import get_password_hash, create_access_token
from app.core.config import settings

settings.APP_ENV = "test"


@pytest.fixture(scope="module")
def db():
    """Transactional test DB session — rolls back after module execution."""
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def test_user(db):
    user = User(
        email=f"exam_test_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("password123"),
        display_name="Exam Tester",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="module")
def test_topic(db, test_user):
    topic = Topic(
        user_id=test_user.id,
        name="Data Structures Test Topic",
        description="Validation topic for Phase 6",
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@pytest.fixture(scope="module")
def seeded_questions(db, test_user, test_topic):
    """Seed three multiple-choice questions with option order."""
    questions = []
    for i in range(3):
        q = Question(
            user_id=test_user.id,
            topic_id=test_topic.id,
            question_text=f"Sample Question {i+1}",
            explanation=f"Explanation for question {i+1}",
            difficulty="medium",
            generated_by="ai",
        )
        db.add(q)
        db.flush()

        # Seed 4 options per question
        for j in range(4):
            opt = QuestionOption(
                question_id=q.id,
                option_text=f"Option {chr(65+j)}",
                is_correct=(j == 0),  # Option A is always correct
                option_order=j
            )
            db.add(opt)
        
        questions.append(q)
    db.commit()
    for q in questions:
        db.refresh(q)
    return questions


@pytest.fixture(scope="module")
def auth_headers(test_user):
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


class TestExamEngineAPI:

    def test_create_session_endpoint(self, client, auth_headers, test_topic, seeded_questions):
        """POST /api/exams/sessions should return 201 and establish session state."""
        resp = client.post(
            "/api/exams/sessions",
            json={
                "topic_id": str(test_topic.id),
                "mode": "practice",
                "difficulty_filter": "medium",
                "question_count": 3,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "in_progress"
        assert body["mode"] == "practice"
        assert len(body["questions"]) == 3
        # In practice mode, explanations should not be leaked initially
        for q in body["questions"]:
            assert q["explanation"] is None
            assert len(q["options"]) == 4

    def test_practice_mode_exposes_correctness_immediately(self, client, auth_headers, test_topic, seeded_questions, db):
        """In practice mode, answer submission returns correctness and correct option ID immediately."""
        # Initialize session
        resp_session = client.post(
            "/api/exams/sessions",
            json={
                "topic_id": str(test_topic.id),
                "mode": "practice",
                "question_count": 1,
            },
            headers=auth_headers,
        )
        session_data = resp_session.json()
        session_id = session_data["id"]
        question = session_data["questions"][0]
        
        # Get correct option ID
        db_q = db.query(Question).filter(Question.id == uuid.UUID(question["id"])).first()
        correct_opt = next(o for o in db_q.options if o.is_correct)
        incorrect_opt = next(o for o in db_q.options if not o.is_correct)

        # Submit incorrect answer
        resp_sub = client.post(
            f"/api/exams/sessions/{session_id}/submit-answer",
            json={
                "question_id": question["id"],
                "selected_option_id": str(incorrect_opt.id),
                "time_taken_seconds": 15,
            },
            headers=auth_headers,
        )
        assert resp_sub.status_code == 200
        sub_data = resp_sub.json()
        assert sub_data["is_correct"] is False
        assert sub_data["correct_option_id"] == str(correct_opt.id)

    def test_timed_mode_hides_correctness(self, client, auth_headers, test_topic, seeded_questions, db):
        """In timed mode, answer submission hides correctness/answers."""
        resp_session = client.post(
            "/api/exams/sessions",
            json={
                "topic_id": str(test_topic.id),
                "mode": "timed",
                "question_count": 1,
            },
            headers=auth_headers,
        )
        session_data = resp_session.json()
        session_id = session_data["id"]
        question = session_data["questions"][0]

        # Submit answer
        db_q = db.query(Question).filter(Question.id == uuid.UUID(question["id"])).first()
        correct_opt = next(o for o in db_q.options if o.is_correct)

        resp_sub = client.post(
            f"/api/exams/sessions/{session_id}/submit-answer",
            json={
                "question_id": question["id"],
                "selected_option_id": str(correct_opt.id),
            },
            headers=auth_headers,
        )
        assert resp_sub.status_code == 200
        sub_data = resp_sub.json()
        assert sub_data["is_correct"] is None
        assert sub_data["correct_option_id"] is None

    def test_scoring_on_explicit_completion(self, client, auth_headers, test_topic, seeded_questions, db):
        """Completing an exam session computes scores correctly based on responses."""
        resp_session = client.post(
            "/api/exams/sessions",
            json={
                "topic_id": str(test_topic.id),
                "mode": "timed",
                "question_count": 3,
            },
            headers=auth_headers,
        )
        session_data = resp_session.json()
        session_id = session_data["id"]

        # Submit 2 correct answers, 1 incorrect
        for idx, question in enumerate(session_data["questions"]):
            db_q = db.query(Question).filter(Question.id == uuid.UUID(question["id"])).first()
            if idx < 2:
                # correct answer
                selected = next(o for o in db_q.options if o.is_correct)
            else:
                # incorrect answer
                selected = next(o for o in db_q.options if not o.is_correct)

            client.post(
                f"/api/exams/sessions/{session_id}/submit-answer",
                json={
                    "question_id": question["id"],
                    "selected_option_id": str(selected.id),
                },
                headers=auth_headers,
            )

        # Complete exam session
        resp_comp = client.post(
            f"/api/exams/sessions/{session_id}/complete",
            headers=auth_headers,
        )
        assert resp_comp.status_code == 200
        comp_data = resp_comp.json()
        assert comp_data["status"] == "completed"
        # 2 out of 3 is 66.67%
        assert comp_data["score"] == 66.67
        # Once completed, explanations must be revealed
        for q in comp_data["questions"]:
            assert q["explanation"] is not None

    def test_timing_lockout_enforced(self, client, auth_headers, test_topic, seeded_questions, db):
        """Submitting answer to an expired timed exam locks session and raises 400."""
        # Start a short timed session (e.g. 5 seconds)
        resp_session = client.post(
            "/api/exams/sessions",
            json={
                "topic_id": str(test_topic.id),
                "mode": "timed",
                "question_count": 1,
                "time_limit_seconds": 1,
            },
            headers=auth_headers,
        )
        session_data = resp_session.json()
        session_id = uuid.UUID(session_data["id"])
        question_id = session_data["questions"][0]["id"]

        # Backdate started_at in the database to simulate timeout
        session_record = db.query(ExamSession).filter(ExamSession.id == session_id).first()
        session_record.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()

        # Try submitting an answer after backdating
        resp_sub = client.post(
            f"/api/exams/sessions/{session_id}/submit-answer",
            json={
                "question_id": question_id,
            },
            headers=auth_headers,
        )
        assert resp_sub.status_code == 400
        assert "Time limit exceeded" in resp_sub.json()["detail"]

        # Verify session status changed to completed
        db.refresh(session_record)
        assert session_record.status == "completed"
