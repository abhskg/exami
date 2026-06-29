import os

import pytest
from fastapi import status

from app.core.config import settings
from app.models.content_chunk import ContentChunk
from app.models.document import Document
from app.models.job import Job
from app.models.topic import Topic
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

