import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.content_chunk import ContentChunk
from app.models.document import Document
from app.models.question import Question, QuestionOption, question_tags
from app.models.tag import Tag
from app.models.topic import Topic
from app.models.user import User

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
        email=f"manage_test_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("password123"),
        display_name="Manager Tester",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="module")
def test_topic(db, test_user):
    topic = Topic(
        user_id=test_user.id,
        name="Management Test Topic",
        description="Validation topic for Phase 8 Management Catalog",
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@pytest.fixture(scope="module")
def auth_headers(test_user):
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


class TestManagementAPI:

    def test_document_rename_and_delete(self, client, auth_headers, test_topic, db):
        """PUT /api/documents/{id} renames, DELETE /api/documents/{id} deletes document."""
        # 1. Create document
        doc = Document(
            user_id=test_topic.user_id,
            topic_id=test_topic.id,
            source_type="manual_topic_text",
            original_filename="initial_doc_name.txt",
            status="parsed",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Add a chunk to verify cascade delete
        chunk = ContentChunk(
            document_id=doc.id,
            user_id=test_topic.user_id,
            topic_id=test_topic.id,
            chunk_text="Some chunk content text",
            chunk_index=0,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        # 2. Rename document
        resp_rename = client.put(
            f"/api/documents/{doc.id}",
            json={"original_filename": "renamed_doc_name.txt"},
            headers=auth_headers,
        )
        assert resp_rename.status_code == 200, resp_rename.text
        assert resp_rename.json()["original_filename"] == "renamed_doc_name.txt"

        # Verify DB
        db.refresh(doc)
        assert doc.original_filename == "renamed_doc_name.txt"

        # 3. Retrieve chunks
        resp_chunks = client.get(f"/api/documents/{doc.id}/chunks", headers=auth_headers)
        assert resp_chunks.status_code == 200
        assert len(resp_chunks.json()) == 1
        assert resp_chunks.json()[0]["chunk_text"] == "Some chunk content text"

        # 4. Delete document
        resp_delete = client.delete(
            f"/api/documents/{doc.id}",
            headers=auth_headers,
        )
        assert resp_delete.status_code == 200

        # Verify cascade deletion
        deleted_doc = db.query(Document).filter(Document.id == doc.id).first()
        assert deleted_doc is None

        deleted_chunk = db.query(ContentChunk).filter(ContentChunk.id == chunk.id).first()
        assert deleted_chunk is None

    def test_chunk_edit_and_delete(self, client, auth_headers, test_topic, db):
        """PUT /api/documents/chunks/{id} edits text/regenerates vector, DELETE deletes chunk."""
        # Create a temp document and chunk
        doc = Document(
            user_id=test_topic.user_id,
            topic_id=test_topic.id,
            source_type="manual_topic_text",
            original_filename="chunk_test.txt",
            status="parsed",
        )
        db.add(doc)
        db.commit()

        chunk = ContentChunk(
            document_id=doc.id,
            user_id=test_topic.user_id,
            topic_id=test_topic.id,
            chunk_text="Initial chunk text content.",
            chunk_index=0,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        # Edit chunk
        resp_edit = client.put(
            f"/api/documents/chunks/{chunk.id}",
            json={"chunk_text": "Updated chunk text content is longer."},
            headers=auth_headers,
        )
        assert resp_edit.status_code == 200, resp_edit.text
        assert resp_edit.json()["chunk_text"] == "Updated chunk text content is longer."

        # Verify DB
        db.refresh(chunk)
        assert chunk.chunk_text == "Updated chunk text content is longer."
        # Embedding should have been generated (mock generator produces a list of 768 elements in tests)
        assert chunk.embedding is not None

        # Delete chunk
        resp_del = client.delete(f"/api/documents/chunks/{chunk.id}", headers=auth_headers)
        assert resp_del.status_code == 200

        deleted_chunk = db.query(ContentChunk).filter(ContentChunk.id == chunk.id).first()
        assert deleted_chunk is None

    def test_question_edit_and_delete(self, client, auth_headers, test_topic, db):
        """PUT /api/questions/{id} updates question/choices/tags, DELETE deletes question."""
        # 1. Seed initial question, options, and tags
        q = Question(
            user_id=test_topic.user_id,
            topic_id=test_topic.id,
            question_text="Initial question statement?",
            difficulty="easy",
            explanation="Initial explanation",
            generated_by="manual",
        )
        db.add(q)
        db.flush()

        opt1 = QuestionOption(
            question_id=q.id, option_text="Opt A", is_correct=True, option_order=0
        )
        opt2 = QuestionOption(
            question_id=q.id, option_text="Opt B", is_correct=False, option_order=1
        )
        db.add(opt1)
        db.add(opt2)

        tag = Tag(user_id=test_topic.user_id, topic_id=test_topic.id, name="initial_tag")
        db.add(tag)
        db.flush()
        db.execute(question_tags.insert().values(question_id=q.id, tag_id=tag.id))
        db.commit()
        db.refresh(q)

        # 2. Update question
        resp_update = client.put(
            f"/api/questions/{q.id}",
            json={
                "question_text": "Updated question statement?",
                "explanation": "Updated explanation statement",
                "difficulty": "hard",
                "tags": ["updated_tag", "new_concept"],
                "options": [
                    {
                        "option_text": "New Opt A (Incorrect)",
                        "is_correct": False,
                        "option_order": 0,
                    },
                    {"option_text": "New Opt B (Correct)", "is_correct": True, "option_order": 1},
                ],
            },
            headers=auth_headers,
        )
        assert resp_update.status_code == 200, resp_update.text
        body = resp_update.json()
        assert body["question_text"] == "Updated question statement?"
        assert body["difficulty"] == "hard"
        assert body["explanation"] == "Updated explanation statement"
        assert len(body["options"]) == 2
        assert body["options"][0]["option_text"] == "New Opt A (Incorrect)"
        assert body["options"][1]["is_correct"] is True
        assert set(body["tags"]) == {"updated_tag", "new_concept"}

        # 3. Delete question
        resp_del = client.delete(f"/api/questions/{q.id}", headers=auth_headers)
        assert resp_del.status_code == 200

        deleted_q = db.query(Question).filter(Question.id == q.id).first()
        assert deleted_q is None

    def test_tag_rename_merge_and_delete(self, client, auth_headers, test_topic, db):
        """PUT /api/questions/tags/{id} renames/merges, DELETE deletes tag."""
        # 1. Create two tags
        t1 = Tag(user_id=test_topic.user_id, topic_id=test_topic.id, name="tag_one")
        t2 = Tag(user_id=test_topic.user_id, topic_id=test_topic.id, name="tag_two")
        db.add(t1)
        db.add(t2)
        db.flush()

        # Create a question linked to tag_one
        q = Question(
            user_id=test_topic.user_id,
            topic_id=test_topic.id,
            question_text="Linked to tag one?",
            difficulty="easy",
            generated_by="manual",
        )
        db.add(q)
        db.flush()
        db.execute(question_tags.insert().values(question_id=q.id, tag_id=t1.id))
        db.commit()

        # 2. Rename tag_one -> tag_three (simple rename)
        resp_rename = client.put(
            f"/api/questions/tags/{t1.id}", json={"name": "tag_three"}, headers=auth_headers
        )
        assert resp_rename.status_code == 200
        assert resp_rename.json()["name"] == "tag_three"

        db.refresh(t1)
        assert t1.name == "tag_three"

        # 3. Rename tag_three -> tag_two (merges with existing tag_two!)
        resp_merge = client.put(
            f"/api/questions/tags/{t1.id}", json={"name": "tag_two"}, headers=auth_headers
        )
        assert resp_merge.status_code == 200
        # Should return existing tag_two
        assert resp_merge.json()["id"] == str(t2.id)
        assert resp_merge.json()["name"] == "tag_two"

        # Verify tag_one (now old tag) was deleted
        deleted_t1 = db.query(Tag).filter(Tag.id == t1.id).first()
        assert deleted_t1 is None

        # Verify question is now linked to tag_two
        link = db.execute(
            text("SELECT 1 FROM question_tags WHERE question_id = :qid AND tag_id = :tid"),
            {"qid": q.id, "tid": t2.id},
        ).first()
        assert link is not None

        # 4. Delete tag_two
        resp_del = client.delete(f"/api/questions/tags/{t2.id}", headers=auth_headers)
        assert resp_del.status_code == 200

        deleted_t2 = db.query(Tag).filter(Tag.id == t2.id).first()
        assert deleted_t2 is None


def test_document_delete_handles_physical_file_exception(client, auth_headers, test_topic, db):
    # Create document with an invalid storage path (a directory) to force exception during deletion
    doc = Document(
        user_id=test_topic.user_id,
        topic_id=test_topic.id,
        source_type="manual_topic_text",
        original_filename="un-deletable-file.txt",
        storage_path=".",  # a directory, exists but cannot be deleted via os.remove
        status="parsed",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    resp_delete = client.delete(f"/api/documents/{doc.id}", headers=auth_headers)
    assert resp_delete.status_code == 200
    assert resp_delete.json()["message"] == "Document deleted successfully."

    # Verify document is still deleted from database
    deleted_doc = db.query(Document).filter(Document.id == doc.id).first()
    assert deleted_doc is None

