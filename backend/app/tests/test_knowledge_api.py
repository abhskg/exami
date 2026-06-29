import os
import shutil
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import status

from app.models.document import Document
from app.models.user import User
from app.tests.test_ingestion import get_auth_headers


@pytest.fixture
def seeded_okf_document(db, client):
    headers = get_auth_headers(client)
    user = db.query(User).filter(User.email == "ingestiontest@example.com").first()

    # Create topic
    res_topic = client.post("/api/topics/", json={"name": "OKF API Topic", "description": "Topic for OKF test"}, headers=headers)
    topic_id = uuid.UUID(res_topic.json()["id"])

    # Create fake OKF directory structure
    okf_dir = f"./data/knowledge/{user.id}/{topic_id}"
    concepts_dir = Path(okf_dir) / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write index.md
    with open(Path(okf_dir) / "index.md", "w", encoding="utf-8") as f:
        f.write("# OKF Index\n\n- [Arrays](./concepts/arrays.md)\n")

    # 2. Write concept file
    with open(concepts_dir / "arrays.md", "w", encoding="utf-8") as f:
        f.write("---\ntitle: Arrays\ndescription: Contiguous block\n---\n# Arrays\nBody text.")

    # Seed Document
    doc = Document(
        user_id=user.id,
        topic_id=topic_id,
        source_type="web_scan",
        original_filename="web_scan_seeded",
        status="parsed",
        okf_directory_path=okf_dir,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    yield doc, headers

    # Cleanup OKF files
    if os.path.exists(okf_dir):
        shutil.rmtree(okf_dir)


def test_get_knowledge_graph(client, seeded_okf_document):
    doc, headers = seeded_okf_document
    res = client.get(f"/api/knowledge/{doc.topic_id}/graph", headers=headers)
    assert res.status_code == 200
    graph = res.json()
    assert "nodes" in graph
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["id"] == "arrays"


def test_get_concept_body(client, seeded_okf_document):
    doc, headers = seeded_okf_document
    res = client.get(f"/api/knowledge/{doc.topic_id}/concept/arrays", headers=headers)
    assert res.status_code == 200
    assert "# Arrays" in res.json()["body"]

    # Query non-existent slug
    res_fail = client.get(f"/api/knowledge/{doc.topic_id}/concept/non-existent", headers=headers)
    assert res_fail.status_code == 404


@patch("app.api.knowledge.finalize_web_search_task")
def test_review_concepts_endpoint(mock_finalize, client, seeded_okf_document):
    doc, headers = seeded_okf_document
    job_id = uuid.uuid4()
    
    res = client.post(
        f"/api/knowledge/{doc.topic_id}/review",
        json={
            "document_id": str(doc.id),
            "job_id": str(job_id),
            "approved_concepts": [{"slug": "arrays"}],
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"
    mock_finalize.assert_called_once_with(job_id, doc.id, doc.user_id, [{"slug": "arrays"}])


@patch("app.api.knowledge.expand_okf_concept")
@patch("app.workers.ingestion.update_concept_embeddings_task")
def test_deepen_concept_endpoint(mock_update_task, mock_expand, client, seeded_okf_document):
    doc, headers = seeded_okf_document
    mock_expand.return_value = ("New content body", ["arrays", "sub-array"])

    res = client.post(
        f"/api/knowledge/{doc.topic_id}/concept/arrays/deepen",
        json={
            "mode": "merge",
            "new_raw_data": "More details about sub-arrays"
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert "New content body" in res.json()["updated_content"]
    mock_update_task.assert_called_once_with(
        doc.id,
        doc.topic_id,
        doc.user_id,
        doc.okf_directory_path,
        ["arrays", "sub-array"]
    )
