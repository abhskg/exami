import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.topic import Topic
from app.models.document import Document
from app.models.content_chunk import ContentChunk
from app.models.tag import Tag
from app.models.question import Question, QuestionOption
from app.models.question_set import QuestionSet, QuestionSetItem
from app.models.exam import ExamSession, ExamResponse

def test_create_and_link_all_models(db: Session):
    # 1. Create a User
    user = User(
        email="test_models@example.com",
        password_hash="hashed_pw_123",
        display_name="Test Model User",
        plan_tier="free"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None

    # 2. Create a Topic
    topic = Topic(
        user_id=user.id,
        name="Computer Science 101",
        description="Introduction to Algorithms"
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    assert topic.id is not None
    assert topic.user_id == user.id

    # 3. Create a Document
    doc = Document(
        user_id=user.id,
        topic_id=topic.id,
        source_type="upload_pdf",
        original_filename="syllabus.pdf",
        storage_path="/local/path/syllabus.pdf",
        status="parsed"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    assert doc.id is not None
    assert doc.topic_id == topic.id

    # 4. Create a ContentChunk with a mock 768-dimension vector
    mock_embedding = [0.1] * 768
    chunk = ContentChunk(
        document_id=doc.id,
        user_id=user.id,
        topic_id=topic.id,
        chunk_text="An algorithm is a finite sequence of rigorous instructions.",
        embedding=mock_embedding,
        chunk_index=0
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    assert chunk.id is not None
    assert len(chunk.embedding) == 768

    # 5. Create Tags (with hierarchy)
    parent_tag = Tag(
        user_id=user.id,
        topic_id=topic.id,
        name="Algorithms",
        created_by="user_defined"
    )
    db.add(parent_tag)
    db.commit()
    db.refresh(parent_tag)

    sub_tag = Tag(
        user_id=user.id,
        topic_id=topic.id,
        name="Sorting",
        parent_tag_id=parent_tag.id,
        created_by="ai_generated"
    )
    db.add(sub_tag)
    db.commit()
    db.refresh(sub_tag)

    assert sub_tag.parent_tag_id == parent_tag.id
    assert parent_tag.sub_tags[0].id == sub_tag.id

    # Test Tag Unique Constraint (user_id, topic_id, name)
    # Use nested transaction savepoint to avoid rolling back the outer transaction
    nested = db.begin_nested()
    try:
        duplicate_tag = Tag(
            user_id=user.id,
            topic_id=topic.id,
            name="Algorithms"
        )
        db.add(duplicate_tag)
        db.flush()
        pytest.fail("IntegrityError was not raised for duplicate tag unique constraint")
    except IntegrityError:
        nested.rollback()  # Rollback the duplicate tag insert in the savepoint
    else:
        nested.commit()

    # 6. Create Question & Options
    question = Question(
        user_id=user.id,
        topic_id=topic.id,
        source_chunk_id=chunk.id,
        question_text="Which algorithm is an example of divide-and-conquer?",
        explanation="Merge sort recursively splits the array and merges it.",
        difficulty="medium",
        generated_by="ai",
        is_active=True
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    # Link Question to Tags
    question.tags.append(parent_tag)
    question.tags.append(sub_tag)
    db.commit()

    option1 = QuestionOption(
        question_id=question.id,
        option_text="Bubble Sort",
        is_correct=False,
        option_order=0
    )
    option2 = QuestionOption(
        question_id=question.id,
        option_text="Merge Sort",
        is_correct=True,
        option_order=1
    )
    db.add_all([option1, option2])
    db.commit()
    db.refresh(question)

    assert len(question.options) == 2
    assert len(question.tags) == 2
    assert question.source_chunk.id == chunk.id
    assert question.options[1].is_correct is True

    # 7. Create QuestionSet & Set Items
    qset = QuestionSet(
        user_id=user.id,
        topic_id=topic.id,
        name="Midterm Practice Set",
        generation_scope={"tags": ["Algorithms"]}
    )
    db.add(qset)
    db.commit()
    db.refresh(qset)

    qset_item = QuestionSetItem(
        question_set_id=qset.id,
        question_id=question.id,
        position=1
    )
    db.add(qset_item)
    db.commit()
    db.refresh(qset)

    assert len(qset.items) == 1
    assert qset.items[0].question_id == question.id
    assert qset.items[0].position == 1

    # 8. Create Exam Session & Responses
    exam_session = ExamSession(
        user_id=user.id,
        topic_id=topic.id,
        question_set_id=qset.id,
        mode="timed",
        question_count=1,
        time_limit_seconds=1800,
        status="in_progress"
    )
    db.add(exam_session)
    db.commit()
    db.refresh(exam_session)
    assert exam_session.id is not None

    exam_response = ExamResponse(
        exam_session_id=exam_session.id,
        question_id=question.id,
        selected_option_id=option2.id,
        is_correct=True,
        time_taken_seconds=45
    )
    db.add(exam_response)
    db.commit()
    db.refresh(exam_session)

    assert len(exam_session.responses) == 1
    assert exam_session.responses[0].is_correct is True
    assert exam_session.responses[0].selected_option_id == option2.id

    # 9. Verify Cascades (Deleting the Topic should Cascade delete Documents, Tags, Questions, Exam Sessions, etc.)
    db.delete(topic)
    db.commit()

    # Query to check deletion cascades
    assert db.query(Topic).filter_by(id=topic.id).first() is None
    assert db.query(Document).filter_by(id=doc.id).first() is None
    assert db.query(ContentChunk).filter_by(id=chunk.id).first() is None
    assert db.query(Tag).filter_by(id=parent_tag.id).first() is None
    assert db.query(Question).filter_by(id=question.id).first() is None
    assert db.query(QuestionOption).filter_by(id=option1.id).first() is None
    assert db.query(QuestionSet).filter_by(id=qset.id).first() is None
    assert db.query(ExamSession).filter_by(id=exam_session.id).first() is None
    assert db.query(ExamResponse).filter_by(id=exam_response.id).first() is None
