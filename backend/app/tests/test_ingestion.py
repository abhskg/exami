import os

import pytest
from fastapi import status

from app.core.config import settings
from app.models.content_chunk import ContentChunk
from app.models.document import Document
from app.models.job import Job
from app.models.topic import Topic
from app.models.user import User
from app.workers.ingestion import process_document_task, process_web_search_task


def get_auth_headers(client):
    email = "ingestiontest@example.com"
    password = "password123"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": "Test User"},
    )
    login_response = client.post("/api/auth/login", json={"email": email, "password": password})
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_topic_endpoints(client, db):
    headers = get_auth_headers(client)

    # 1. Create a Topic
    res = client.post(
        "/api/topics/",
        json={
            "name": "Database Systems",
            "description": "Relational Databases and SQL",
        },
        headers=headers,
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["name"] == "Database Systems"
    topic_id = data["id"]

    # 2. Get Topics
    res = client.get("/api/topics/", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    topics = res.json()
    assert len(topics) >= 1
    assert topics[0]["id"] == topic_id


def test_upload_validations(client, db):
    headers = get_auth_headers(client)

    # Create topic
    res = client.post(
        "/api/topics/",
        json={"name": "Syllabus Topic", "description": "Testing uploads"},
        headers=headers,
    )
    topic_id = res.json()["id"]

    # 1. Reject invalid file type
    files = {"file": ("script.py", b"print('hello')", "text/x-python")}
    res = client.post(
        "/api/documents/upload",
        data={"topic_id": topic_id},
        files=files,
        headers=headers,
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only PDF, TXT, and MD files are allowed" in res.json()["detail"]

    # 2. Reject size exceeding MAX_FILE_SIZE_MB
    large_content = b"x" * (settings.MAX_FILE_SIZE_MB * 1024 * 1024 + 100)
    files = {"file": ("large.txt", large_content, "text/plain")}
    res = client.post(
        "/api/documents/upload",
        data={"topic_id": topic_id},
        files=files,
        headers=headers,
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert f"exceeds the maximum limit of {settings.MAX_FILE_SIZE_MB}MB" in res.json()["detail"]


def test_successful_upload_and_polling(client, db):
    headers = get_auth_headers(client)

    # Create topic
    res = client.post(
        "/api/topics/",
        json={"name": "Algorithms & Complexity", "description": "CS Course"},
        headers=headers,
    )
    topic_id = res.json()["id"]

    # Upload text file
    file_content = (
        b"This is content chunk 1. We love databases. This is content chunk 2. Sorting is cool."
    )
    files = {"file": ("syllabus.txt", file_content, "text/plain")}

    res = client.post(
        "/api/documents/upload",
        data={"topic_id": topic_id},
        files=files,
        headers=headers,
    )
    assert res.status_code == status.HTTP_202_ACCEPTED
    data = res.json()
    assert "document" in data
    assert "job_id" in data

    document_id = data["document"]["id"]
    job_id = data["job_id"]

    # Verify records created in pending state
    doc_in_db = db.query(Document).filter(Document.id == document_id).first()
    assert doc_in_db is not None
    assert doc_in_db.status == "pending"
    assert doc_in_db.original_filename == "syllabus.txt"
    assert os.path.exists(doc_in_db.storage_path)

    job_in_db = db.query(Job).filter(Job.id == job_id).first()
    assert job_in_db is not None
    assert job_in_db.status == "pending"

    # Verify Job polling endpoint
    poll_res = client.get(f"/api/jobs/{job_id}", headers=headers)
    assert poll_res.status_code == status.HTTP_200_OK
    assert poll_res.json()["status"] == "pending"

    # Retrieve user_id for the test execution
    user_id = doc_in_db.user_id

    # Run the worker task synchronously to test logic
    process_document_task(job_in_db.id, doc_in_db.id, user_id, db=db)

    # Refresh DB session state
    db.expire_all()

    # Verify job and document completed
    assert doc_in_db.status == "parsed"
    assert job_in_db.status == "completed"
    assert job_in_db.progress == 100

    # Verify content chunks populated
    chunks = db.query(ContentChunk).filter(ContentChunk.document_id == document_id).all()
    assert len(chunks) > 0
    assert chunks[0].chunk_text is not None
    assert len(chunks[0].embedding) == 768

    # Verify documents list endpoint
    list_docs_res = client.get(f"/api/documents/?topic_id={topic_id}", headers=headers)
    assert list_docs_res.status_code == status.HTTP_200_OK
    docs = list_docs_res.json()
    assert len(docs) == 1
    assert docs[0]["id"] == str(document_id)
    assert docs[0]["status"] == "parsed"

    # Cleanup file
    if os.path.exists(doc_in_db.storage_path):
        os.remove(doc_in_db.storage_path)


def test_raw_text_ingestion(client, db):
    headers = get_auth_headers(client)

    # Create topic
    res = client.post(
        "/api/topics/",
        json={"name": "Raw Text Topic", "description": "Testing raw text"},
        headers=headers,
    )
    topic_id = res.json()["id"]

    # Ingest raw text
    res = client.post(
        "/api/documents/raw-text",
        json={
            "topic_id": topic_id,
            "title": "Raw text sample",
            "content": "This is a raw text content chunk for testing. It has multiple sentences to be parsed.",
        },
        headers=headers,
    )
    assert res.status_code == status.HTTP_202_ACCEPTED
    data = res.json()
    assert "document" in data
    assert "job_id" in data

    document_id = data["document"]["id"]
    job_id = data["job_id"]

    doc_in_db = db.query(Document).filter(Document.id == document_id).first()
    assert doc_in_db is not None
    assert doc_in_db.status == "pending"
    assert doc_in_db.source_type == "manual_topic_text"
    assert os.path.exists(doc_in_db.storage_path)

    # Run the worker synchronously
    process_document_task(job_id, document_id, doc_in_db.user_id, db=db)

    db.expire_all()
    assert doc_in_db.status == "parsed"

    # Cleanup file
    if os.path.exists(doc_in_db.storage_path):
        os.remove(doc_in_db.storage_path)


def test_web_search_ingestion(client, db):
    headers = get_auth_headers(client)

    # Create topic
    res = client.post(
        "/api/topics/",
        json={"name": "Web Search Topic", "description": "Testing web search"},
        headers=headers,
    )
    topic_id = res.json()["id"]

    # Ingest web search placeholder
    res = client.post(
        "/api/documents/web-search",
        json={
            "topic_id": topic_id,
            "title": "Web search sample",
            "syllabus": "List of sorting algorithms",
            "topics": "QuickSort, MergeSort, BubbleSort",
        },
        headers=headers,
    )
    assert res.status_code == status.HTTP_202_ACCEPTED
    data = res.json()
    assert "document" in data
    assert "job_id" in data

    document_id = data["document"]["id"]
    job_id = data["job_id"]

    doc_in_db = db.query(Document).filter(Document.id == document_id).first()
    assert doc_in_db is not None
    assert doc_in_db.status == "pending"
    assert doc_in_db.source_type == "web_scan"
    assert os.path.exists(doc_in_db.storage_path)

    # Run the worker synchronously using the web search parser agent task
    process_web_search_task(
        job_id,
        document_id,
        doc_in_db.user_id,
        "Web search sample",
        "List of sorting algorithms",
        "QuickSort, MergeSort, BubbleSort",
        db=db,
    )

    db.expire_all()
    job_in_db = db.query(Job).filter(Job.id == job_id).first()
    assert job_in_db.status == "awaiting_review"
    assert doc_in_db.status == "parsing"

    # Verify staging JSON exists
    staging_path = os.path.join(settings.DATA_DIR, "staging", f"{job_id}.json")
    assert os.path.exists(staging_path)

    import json
    with open(staging_path, "r", encoding="utf-8") as f:
        approved_concepts = json.load(f)
    assert len(approved_concepts) > 0

    # Run the finalization worker synchronously
    from app.workers.ingestion import finalize_web_search_task
    finalize_web_search_task(
        job_id,
        document_id,
        doc_in_db.user_id,
        approved_concepts,
        db=db,
    )

    db.expire_all()
    assert doc_in_db.status == "parsed"
    assert job_in_db.status == "completed"
    assert doc_in_db.okf_directory_path is not None
    assert os.path.exists(doc_in_db.okf_directory_path)

    # Verify log and index files
    assert os.path.exists(os.path.join(doc_in_db.okf_directory_path, "index.md"))
    assert os.path.exists(os.path.join(doc_in_db.okf_directory_path, "log.md"))

    # Cleanup staging file (should be deleted by finalization task)
    assert not os.path.exists(staging_path)

    # Cleanup OKF directory and storage path parameters file
    import shutil
    if os.path.exists(doc_in_db.okf_directory_path):
        shutil.rmtree(doc_in_db.okf_directory_path)
    if os.path.exists(doc_in_db.storage_path):
        os.remove(doc_in_db.storage_path)


def test_web_search_ingest_request_relaxed_limits():
    from app.api.documents import WebSearchIngestRequest
    import uuid
    # Generate a syllabus of 95,000 characters
    large_syllabus = "a" * 95000
    large_topics = "b" * 95000
    req = WebSearchIngestRequest(
        topic_id=uuid.uuid4(),
        title="Large Input Ingest",
        syllabus=large_syllabus,
        topics=large_topics
    )
    assert req.syllabus == large_syllabus
    assert req.topics == large_topics


def test_update_topic_endpoint(client, db):
    headers = get_auth_headers(client)
    import uuid

    # Create two topics
    res1 = client.post("/api/topics/", json={"name": "Topic A", "description": "Desc A"}, headers=headers)
    res2 = client.post("/api/topics/", json={"name": "Topic B", "description": "Desc B"}, headers=headers)
    topic_a_id = res1.json()["id"]
    topic_b_id = res2.json()["id"]

    # Rename Topic A to Topic C (should succeed)
    res_update = client.put(f"/api/topics/{topic_a_id}", json={"name": "Topic C", "description": "New Desc A"}, headers=headers)
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Topic C"
    assert res_update.json()["description"] == "New Desc A"

    # Rename Topic B to Topic C (should fail due to conflict name)
    res_conflict = client.put(f"/api/topics/{topic_b_id}", json={"name": "Topic C"}, headers=headers)
    assert res_conflict.status_code == 400
    assert "already exists" in res_conflict.json()["detail"]

    # Update topic that doesn't exist
    res_not_found = client.put(f"/api/topics/{uuid.uuid4()}", json={"name": "Topic X"}, headers=headers)
    assert res_not_found.status_code == 404


def test_delete_topic_endpoint(client, db):
    headers = get_auth_headers(client)
    import uuid

    # Create topic
    res = client.post("/api/topics/", json={"name": "Topic to Delete", "description": "Will be deleted"}, headers=headers)
    topic_id = res.json()["id"]

    # Delete topic
    res_del = client.delete(f"/api/topics/{topic_id}", headers=headers)
    assert res_del.status_code == 204

    # Verify it is deleted in database
    res_get = client.get("/api/topics/", headers=headers)
    topic_ids = [t["id"] for t in res_get.json()]
    assert topic_id not in topic_ids

    # Delete topic that doesn't exist (should 404)
    res_del_not_found = client.delete(f"/api/topics/{uuid.uuid4()}", headers=headers)
    assert res_del_not_found.status_code == 404


def test_reparse_document_endpoint_validations(client, db):
    headers = get_auth_headers(client)
    import uuid

    # Create a topic
    res_topic = client.post("/api/topics/", json={"name": "Reparse Topic", "description": "Reparse validations"}, headers=headers)
    topic_id = res_topic.json()["id"]

    # 1. Reject reparsing non-existent document
    res_not_found = client.post(f"/api/documents/{uuid.uuid4()}/reparse", headers=headers)
    assert res_not_found.status_code == 404

    # 2. Seed a parsed document and verify reparse is rejected (409 Conflict)
    doc = Document(
        user_id=db.query(User).filter(User.email == "ingestiontest@example.com").first().id,
        topic_id=uuid.UUID(topic_id),
        source_type="upload_text",
        original_filename="parsed.txt",
        status="parsed",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    res_conflict = client.post(f"/api/documents/{doc.id}/reparse", headers=headers)
    assert res_conflict.status_code == 409
    assert "is not in a failed state" in res_conflict.json()["detail"]


def test_reparse_successful_normal_document(client, db):
    headers = get_auth_headers(client)
    user = db.query(User).filter(User.email == "ingestiontest@example.com").first()
    import uuid

    # Create topic
    res_topic = client.post("/api/topics/", json={"name": "Reparse Topic Success", "description": "Normal doc reparse"}, headers=headers)
    topic_id = res_topic.json()["id"]

    # Seed a failed upload document and some chunks
    doc = Document(
        user_id=user.id,
        topic_id=uuid.UUID(topic_id),
        source_type="upload_text",
        original_filename="failed_doc.txt",
        storage_path="./data/uploads/failed_doc.txt",
        status="failed",
    )
    db.add(doc)
    db.flush()

    chunk = ContentChunk(
        document_id=doc.id,
        user_id=user.id,
        topic_id=uuid.UUID(topic_id),
        chunk_text="Stale chunk text",
        chunk_index=0,
    )
    db.add(chunk)
    db.commit()

    # Create the file on disk so the ingestion worker doesn't fail immediately
    os.makedirs(os.path.dirname(doc.storage_path), exist_ok=True)
    with open(doc.storage_path, "w", encoding="utf-8") as f:
        f.write("New parsed text after reparsing.")

    # Call reparse endpoint
    res_reparse = client.post(f"/api/documents/{doc.id}/reparse", headers=headers)
    assert res_reparse.status_code == 202
    data = res_reparse.json()
    assert data["message"] == "Reparse started successfully."
    
    job_id = uuid.UUID(data["job_id"])

    # Run the document ingestion task synchronously to process the reparse
    process_document_task(job_id, doc.id, user.id, db=db)

    # Verify chunks updated and document status is parsed
    db.expire_all()
    db.refresh(doc)
    assert doc.status == "parsed"

    chunks = db.query(ContentChunk).filter(ContentChunk.document_id == doc.id).all()
    assert len(chunks) == 1
    assert chunks[0].chunk_text == "New parsed text after reparsing."

    # Cleanup file
    if os.path.exists(doc.storage_path):
        os.remove(doc.storage_path)


def test_reparse_web_scan_failures(client, db):
    headers = get_auth_headers(client)
    user = db.query(User).filter(User.email == "ingestiontest@example.com").first()
    import uuid

    # Create topic
    res_topic = client.post("/api/topics/", json={"name": "Reparse Web Scan", "description": "Web scan fail"}, headers=headers)
    topic_id = res_topic.json()["id"]

    # 1. Seed a failed web_scan document with NO metadata storage file
    doc = Document(
        user_id=user.id,
        topic_id=uuid.UUID(topic_id),
        source_type="web_scan",
        original_filename="web_scan_failed",
        storage_path="./data/uploads/missing_metadata.json",
        status="failed",
    )
    db.add(doc)
    db.commit()

    res_missing_meta = client.post(f"/api/documents/{doc.id}/reparse", headers=headers)
    assert res_missing_meta.status_code == 400
    assert "Metadata for web search was not found" in res_missing_meta.json()["detail"]

    # 2. Seed invalid metadata file on disk
    doc.storage_path = "./data/uploads/corrupt_metadata.json"
    db.commit()
    with open(doc.storage_path, "w", encoding="utf-8") as f:
        f.write("{invalid json}")

    res_corrupt_meta = client.post(f"/api/documents/{doc.id}/reparse", headers=headers)
    assert res_corrupt_meta.status_code == 400
    assert "Failed to parse web search metadata" in res_corrupt_meta.json()["detail"]

    # Cleanup
    if os.path.exists(doc.storage_path):
        os.remove(doc.storage_path)


def test_update_concept_embeddings_task(db, client):
    headers = get_auth_headers(client)
    user = db.query(User).filter(User.email == "ingestiontest@example.com").first()
    from app.workers.ingestion import update_concept_embeddings_task
    import uuid
    from pathlib import Path
    import shutil

    # Setup mock directories and create a valid topic
    res_topic = client.post("/api/topics/", json={"name": "Embed Task Topic", "description": "Desc"}, headers=headers)
    topic_id = uuid.UUID(res_topic.json()["id"])
    okf_dir = f"./data/knowledge/{user.id}/{topic_id}"
    concepts_dir = Path(okf_dir) / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    with open(concepts_dir / "stack.md", "w", encoding="utf-8") as f:
        f.write("---\ntitle: Stack\ndescription: LIFO structure\n---\n# Stack\nBody contents.")

    doc = Document(
        user_id=user.id,
        topic_id=topic_id,
        source_type="web_scan",
        original_filename="embed_task_doc",
        status="parsed",
        okf_directory_path=okf_dir,
    )
    db.add(doc)
    db.flush()

    # Insert initial chunk
    chunk = ContentChunk(
        document_id=doc.id,
        user_id=user.id,
        topic_id=topic_id,
        chunk_text="Old chunk stack",
        okf_concept_path="concepts/stack.md",
        chunk_index=0,
    )
    db.add(chunk)
    db.commit()

    # Trigger background update task
    update_concept_embeddings_task(doc.id, topic_id, user.id, okf_dir, ["stack"], db=db)

    # Verify chunk is updated/re-vectorized
    db.expire_all()
    chunks = db.query(ContentChunk).filter(ContentChunk.document_id == doc.id).all()
    assert len(chunks) == 1
    assert chunks[0].chunk_text == "# Stack\nBody contents."

    # Cleanup
    if os.path.exists(okf_dir):
        shutil.rmtree(okf_dir)


def test_finalize_web_search_exception_rollback(db, client):
    # Try running finalization with an invalid document ID to trigger exception
    from app.workers.ingestion import finalize_web_search_task
    import uuid
    invalid_doc_id = uuid.uuid4()
    invalid_job_id = uuid.uuid4()

    # Task should handle exception and not crash the worker thread
    finalize_web_search_task(invalid_job_id, invalid_doc_id, uuid.uuid4(), [], db=db)
    # Execution succeeds without throwing unhandled database exception





