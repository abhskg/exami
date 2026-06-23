"""
test_question_bank.py — Phase 5 integration tests

Covers:
- Task 5.1: get_similar_chunks() returns correct ContentChunk rows with mock embeddings.
- Task 5.2: generate_questions() saves Question, QuestionOption, and Tag rows correctly.
- API: POST /api/questions/generate returns 200 with valid schema.
- API: GET /api/questions/ returns questions filtered by topic.
- API: GET /api/questions/tags returns tag list.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.security import create_access_token, get_password_hash

# ── App imports ──────────────────────────────────────────────────────────────
from app.main import app
from app.models.content_chunk import ContentChunk
from app.models.document import Document
from app.models.question import Question, QuestionOption
from app.models.tag import Tag
from app.models.topic import Topic
from app.models.user import User
from app.services.question_bank import generate_questions, get_similar_chunks, list_topic_tags

# ── Force test environment so mock paths are triggered ──────────────────────
settings.APP_ENV = "test"

# ── Database fixture ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db():
    """Transactional test DB session — rolls back after each module."""
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


# ── Seed helpers ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_user(db):
    user = User(
        email=f"q_test_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("testpass123"),
        display_name="QBank Tester",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="module")
def test_topic(db, test_user):
    topic = Topic(
        user_id=test_user.id,
        name=f"Phase5 Topic {uuid.uuid4().hex[:4]}",
        description="Test topic for Phase 5",
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@pytest.fixture(scope="module")
def test_document(db, test_user, test_topic):
    doc = Document(
        user_id=test_user.id,
        topic_id=test_topic.id,
        source_type="upload_text",
        storage_path="./data/uploads/test_doc.txt",
        original_filename="test_doc.txt",
        status="parsed",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture(scope="module")
def test_chunks(db, test_user, test_topic, test_document):
    """Insert two content chunks with mock zero-vectors."""
    dim = settings.EMBEDDING_DIMENSION
    chunks = []
    for i in range(2):
        chunk = ContentChunk(
            document_id=test_document.id,
            user_id=test_user.id,
            topic_id=test_topic.id,
            chunk_text=f"Test chunk text number {i}: recursion and sorting algorithms.",
            embedding=[0.0] * dim,
            chunk_index=i,
        )
        db.add(chunk)
        chunks.append(chunk)
    db.commit()
    for c in chunks:
        db.refresh(c)
    return chunks


@pytest.fixture(scope="module")
def auth_token(test_user):
    return create_access_token(subject=str(test_user.id))


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ── Task 5.1: Vector Similarity Tests ────────────────────────────────────────


class TestGetSimilarChunks:

    def test_returns_chunks_for_topic(self, db, test_user, test_topic, test_chunks):
        """get_similar_chunks should return chunk rows for the correct topic."""
        results = get_similar_chunks(
            query_text="recursion algorithm",
            topic_id=test_topic.id,
            user_id=test_user.id,
            k=5,
            db=db,
        )
        assert len(results) >= 1
        for chunk in results:
            assert chunk.user_id == test_user.id
            assert chunk.topic_id == test_topic.id

    def test_respects_k_limit(self, db, test_user, test_topic, test_chunks):
        """k parameter limits returned rows."""
        results = get_similar_chunks(
            query_text="algorithms",
            topic_id=test_topic.id,
            user_id=test_user.id,
            k=1,
            db=db,
        )
        assert len(results) <= 1

    def test_wrong_user_returns_empty(self, db, test_topic, test_chunks):
        """Chunks of another user should not be returned."""
        alien_user_id = uuid.uuid4()
        results = get_similar_chunks(
            query_text="recursion",
            topic_id=test_topic.id,
            user_id=alien_user_id,
            k=10,
            db=db,
        )
        assert results == []

    def test_wrong_topic_returns_empty(self, db, test_user, test_chunks):
        """Chunks of another topic should not be returned."""
        alien_topic_id = uuid.uuid4()
        results = get_similar_chunks(
            query_text="sorting",
            topic_id=alien_topic_id,
            user_id=test_user.id,
            k=10,
            db=db,
        )
        assert results == []

    def test_requires_db_session(self):
        """Calling without db should raise ValueError."""
        with pytest.raises(ValueError, match="database session"):
            get_similar_chunks("test", uuid.uuid4(), uuid.uuid4(), db=None)


# ── Task 5.2: MCQ Generation Tests ───────────────────────────────────────────


class TestGenerateQuestions:

    def test_generates_and_saves_questions(self, db, test_user, test_topic, test_chunks):
        """generate_questions should create Question and QuestionOption rows."""
        saved = generate_questions(
            topic_id=test_topic.id,
            user_id=test_user.id,
            count=1,
            difficulty="medium",
            tag_filters=[],
            db=db,
        )
        assert len(saved) >= 1
        q = saved[0]
        assert isinstance(q, Question)
        assert q.user_id == test_user.id
        assert q.topic_id == test_topic.id
        assert q.question_text
        assert len(q.options) == 4

    def test_each_question_has_one_correct_option(self, db, test_user, test_topic, test_chunks):
        """Each generated question must have exactly one correct option."""
        saved = generate_questions(
            topic_id=test_topic.id,
            user_id=test_user.id,
            count=1,
            difficulty="easy",
            tag_filters=[],
            db=db,
        )
        for q in saved:
            correct = [o for o in q.options if o.is_correct]
            assert len(correct) == 1, f"Expected 1 correct option, got {len(correct)}"

    def test_tags_are_created_and_linked(self, db, test_user, test_topic, test_chunks):
        """Tags returned by Gemini mock should be persisted and linked to questions."""
        saved = generate_questions(
            topic_id=test_topic.id,
            user_id=test_user.id,
            count=1,
            difficulty="medium",
            tag_filters=[],
            db=db,
        )
        q = saved[0]
        # In test/mock mode the mock MCQ always has tags ["mock", "test"]
        assert len(q.tags) >= 1

    def test_duplicate_tags_not_created(self, db, test_user, test_topic, test_chunks):
        """Running generation twice should not duplicate tags."""
        before = (
            db.query(Tag)
            .filter(
                Tag.user_id == test_user.id,
                Tag.topic_id == test_topic.id,
            )
            .count()
        )

        generate_questions(
            topic_id=test_topic.id,
            user_id=test_user.id,
            count=1,
            difficulty="medium",
            tag_filters=[],
            db=db,
        )

        after = (
            db.query(Tag)
            .filter(
                Tag.user_id == test_user.id,
                Tag.topic_id == test_topic.id,
            )
            .count()
        )

        # Should reuse existing tags — at most 2 new ones (mock + test), likely 0
        assert after - before <= 2

    def test_list_topic_tags(self, db, test_user, test_topic, test_chunks):
        """list_topic_tags should return all tags alphabetically."""
        # Generate so tags exist
        generate_questions(
            topic_id=test_topic.id,
            user_id=test_user.id,
            count=1,
            difficulty="medium",
            tag_filters=[],
            db=db,
        )
        tags = list_topic_tags(test_topic.id, test_user.id, db)
        names = [t.name for t in tags]
        assert names == sorted(names)


# ── API Endpoint Tests ────────────────────────────────────────────────────────


class TestQuestionsAPI:

    def test_generate_endpoint_returns_200(self, client, auth_headers, test_topic):
        """POST /api/questions/generate should return 200 with generated questions."""
        resp = client.post(
            "/api/questions/generate",
            json={
                "topic_id": str(test_topic.id),
                "count": 1,
                "difficulty": "medium",
                "tag_filters": [],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "generated" in body
        assert "questions" in body
        assert body["generated"] >= 1
        assert len(body["questions"]) >= 1

    def test_generate_validates_difficulty(self, client, auth_headers, test_topic):
        """Invalid difficulty value should return 422."""
        resp = client.post(
            "/api/questions/generate",
            json={
                "topic_id": str(test_topic.id),
                "count": 1,
                "difficulty": "extreme",
                "tag_filters": [],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_generate_wrong_topic_returns_404(self, client, auth_headers):
        """Generating for a non-existent topic should return 404."""
        resp = client.post(
            "/api/questions/generate",
            json={
                "topic_id": str(uuid.uuid4()),
                "count": 1,
                "difficulty": "medium",
                "tag_filters": [],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_generate_requires_auth(self, client, test_topic):
        """Unauthenticated request should return 401."""
        resp = client.post(
            "/api/questions/generate",
            json={
                "topic_id": str(test_topic.id),
                "count": 1,
                "difficulty": "medium",
                "tag_filters": [],
            },
        )
        assert resp.status_code == 401

    def test_list_questions_endpoint(self, client, auth_headers, test_topic):
        """GET /api/questions/ should return a list of questions."""
        resp = client.get(
            f"/api/questions/?topic_id={test_topic.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)

    def test_list_questions_unknown_topic_404(self, client, auth_headers):
        """GET /api/questions/ with unknown topic_id returns 404."""
        resp = client.get(
            f"/api/questions/?topic_id={uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list_tags_endpoint(self, client, auth_headers, test_topic):
        """GET /api/questions/tags should return a list of tag objects."""
        resp = client.get(
            f"/api/questions/tags?topic_id={test_topic.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        for tag in body:
            assert "id" in tag
            assert "name" in tag

    def test_analytics_endpoint(self, client, auth_headers, test_topic):
        """GET /api/questions/analytics should return a QuestionAnalyticsResponse."""
        # 1. Query with specific topic_id
        resp = client.get(
            f"/api/questions/analytics?topic_id={test_topic.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "total_questions" in body
        assert "difficulty_breakdown" in body
        assert "tag_breakdown" in body
        assert "topic_breakdown" in body

        # Verify default difficulty breakdown has easy, medium, hard keys
        diff = body["difficulty_breakdown"]
        assert "easy" in diff
        assert "medium" in diff
        assert "hard" in diff

        # 2. Query without topic_id (global stats)
        resp_global = client.get(
            "/api/questions/analytics",
            headers=auth_headers,
        )
        assert resp_global.status_code == 200
        body_global = resp_global.json()
        assert "total_questions" in body_global
        assert "difficulty_breakdown" in body_global
        assert "tag_breakdown" in body_global
        assert "topic_breakdown" in body_global
