import json
import os
import uuid
from unittest.mock import patch

import pytest
from fastapi import status

from app.core.config import settings
from app.models.job import Job
from app.models.user import User
from app.tests.test_ingestion import get_auth_headers


@pytest.fixture
def user_and_headers(client, db):
    headers = get_auth_headers(client)
    user = db.query(User).filter(User.email == "ingestiontest@example.com").first()
    return user, headers


@pytest.fixture
def staged_job(db, user_and_headers):
    user, _ = user_and_headers
    job = Job(
        user_id=user.id,
        status="awaiting_review",
        task_type="web_scan",
        progress=50,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Create staging folder and json file
    staging_dir = os.path.join(settings.DATA_DIR, "staging")
    os.makedirs(staging_dir, exist_ok=True)
    staging_path = os.path.join(staging_dir, f"{job.id}.json")
    
    concepts = [
        {
            "slug": "data-structures",
            "title": "Data Structures",
            "description": "Ways to store data",
            "body": "## Overview\nArrays, trees, etc.",
            "tags": ["dsa"],
            "confidence": 0.85,
            "flagged": False,
            "flagged_reason": "",
            "depth_level": 1,
        }
    ]
    with open(staging_path, "w", encoding="utf-8") as f:
        json.dump(concepts, f, indent=2)

    yield job

    # Cleanup staging file
    if os.path.exists(staging_path):
        os.remove(staging_path)


def test_get_staged_concepts(client, user_and_headers, staged_job):
    _, headers = user_and_headers
    res = client.get(f"/api/jobs/{staged_job.id}/staged-concepts", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["slug"] == "data-structures"

    # Get staged concepts for non-existent job
    res_not_found = client.get(f"/api/jobs/{uuid.uuid4()}/staged-concepts", headers=headers)
    assert res_not_found.status_code == 404


def test_delete_staged_concept(client, user_and_headers, staged_job):
    _, headers = user_and_headers
    
    # 1. Delete non-existent concept slug
    res_fail = client.delete(f"/api/jobs/{staged_job.id}/staged-concepts/non-existent", headers=headers)
    assert res_fail.status_code == 404

    # 2. Delete valid concept
    res_ok = client.delete(f"/api/jobs/{staged_job.id}/staged-concepts/data-structures", headers=headers)
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "deleted"

    # Verify staging JSON is empty
    staging_path = os.path.join(settings.DATA_DIR, "staging", f"{staged_job.id}.json")
    with open(staging_path, "r", encoding="utf-8") as f:
        concepts = json.load(f)
    assert len(concepts) == 0


@patch("app.services.okf_service._generate_text_with_llm")
def test_refine_staged_concept(mock_llm, client, user_and_headers, staged_job):
    _, headers = user_and_headers
    mock_llm.return_value = "Refined body from LLM."
    
    res = client.post(
        f"/api/jobs/{staged_job.id}/staged-concepts/data-structures/refine",
        json={"prompt": "Make it more thorough"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["updated_body"] == "Refined body from LLM."


@patch("app.services.okf_service._generate_json_with_llm")
def test_suggest_staged_concept_with_slug_collision(mock_llm, client, user_and_headers, staged_job):
    _, headers = user_and_headers
    
    # Force LLM output to conflict with existing 'data-structures' slug
    mock_llm.return_value = {
        "slug": "data-structures",
        "title": "Colliding Title",
        "description": "Will force suffix creation",
        "body": "## Section\nContent",
        "tags": ["dsa"],
        "depth_level": 2,
        "confidence": 0.9,
        "flagged": False,
        "flagged_reason": "",
    }

    res = client.post(
        f"/api/jobs/{staged_job.id}/staged-concepts/suggest",
        json={"topic": "Data Structures"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "added"
    concept = res.json()["concept"]
    assert concept["slug"] == "data-structures-1"  # verify suffix appended due to slug collision
