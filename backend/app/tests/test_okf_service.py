import json
import os
import uuid
from pathlib import Path

import pytest

from app.services.okf_service import (
    append_okf_log,
    chunk_from_okf,
    load_okf_index,
    write_okf_concepts,
)


def test_write_and_load_okf_concepts(tmp_path):
    user_id = uuid.uuid4()
    topic_id = uuid.uuid4()
    okf_dir = str(tmp_path / "okf")

    concepts = [
        {
            "slug": "arrays",
            "title": "Arrays",
            "description": "Contiguous memory blocks",
            "tags": ["dsa", "memory"],
            "related": ["linked-lists"],
            "confidence": 0.9,
            "flagged": False,
            "flagged_reason": "",
            "depth_level": 1,
            "body": "## Definition\nAn array is a data structure...\n## Operations\nO(1) access.",
        },
        {
            "slug": "linked-lists",
            "title": "Linked Lists",
            "description": "Node based sequence",
            "tags": ["dsa", "pointers"],
            "related": ["arrays"],
            "confidence": 0.85,
            "flagged": True,
            "flagged_reason": "Needs more detail",
            "depth_level": 1,
            "body": "## Intro\nNodes with pointers.",
        },
    ]

    # Test Write
    write_okf_concepts(user_id, topic_id, concepts, okf_dir)

    # Assert directories and index files exist
    assert os.path.exists(okf_dir)
    assert os.path.exists(os.path.join(okf_dir, "index.md"))
    assert os.path.exists(os.path.join(okf_dir, "log.md"))
    
    # Assert concept files exist under clustered subdirectories
    concepts_path = Path(okf_dir) / "concepts"
    assert len(list(concepts_path.rglob("arrays.md"))) == 1
    assert len(list(concepts_path.rglob("linked-lists.md"))) == 1

    # Test Load
    graph = load_okf_index(user_id, topic_id, okf_dir)
    nodes = graph["nodes"]
    edges = graph["edges"]

    assert len(nodes) == 2
    assert len(edges) == 2

    # Verify node content parsing
    array_node = next((n for n in nodes if n["id"] == "arrays"), None)
    assert array_node is not None
    assert array_node["title"] == "Arrays"
    assert array_node["description"] == "Contiguous memory blocks"
    assert "dsa" in array_node["tags"]

    ll_node = next((n for n in nodes if n["id"] == "linked-lists"), None)
    assert ll_node is not None
    assert ll_node["title"] == "Linked Lists"

    # Verify edges
    assert {"source": "arrays", "target": "linked-lists"} in edges
    assert {"source": "linked-lists", "target": "arrays"} in edges


def test_chunk_from_okf(tmp_path):
    okf_dir = tmp_path / "concepts"
    okf_dir.mkdir(parents=True, exist_ok=True)

    filepath = okf_dir / "test-concept.md"
    content = """---
title: Test
---
# Test

Intro text here.

## Section 1
Content of section 1.

## Section 2
Content of section 2.
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    chunks = chunk_from_okf([str(filepath)])

    assert len(chunks) == 3
    assert chunks[0][1] == "# Test\n\nIntro text here."
    assert chunks[1][1] == "## Section 1\nContent of section 1."
    assert chunks[2][1] == "## Section 2\nContent of section 2."


def test_load_okf_index_filters_invalid_edges(tmp_path):
    user_id = uuid.uuid4()
    topic_id = uuid.uuid4()
    okf_dir = str(tmp_path / "okf")
    concepts_dir = Path(okf_dir) / "concepts"
    cluster_dir = concepts_dir / "cluster_test"
    cluster_dir.mkdir(parents=True, exist_ok=True)

    # Write a concept that relates to a non-existent concept
    filepath = cluster_dir / "test-slug.md"
    content = """---
type: Concept
title: Test Title
description: Test Description
tags: []
related: ["non-existent-slug"]
confidence: 1.0
flagged: false
flagged_reason:
depth_level: 1
created_at: 2026-06-29T00:00:00Z
updated_at: 2026-06-29T00:00:00Z
---
# Test Title

Test body.
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    graph = load_okf_index(user_id, topic_id, okf_dir)
    assert len(graph["nodes"]) == 1
    assert len(graph["edges"]) == 0


from unittest.mock import patch

@patch("app.services.okf_service._generate_json_with_llm")
def test_expand_okf_concept_resolves_titles_to_slugs(mock_generate, tmp_path):
    user_id = uuid.uuid4()
    topic_id = uuid.uuid4()
    okf_dir = str(tmp_path / "okf")
    concepts_dir = Path(okf_dir) / "concepts"
    cluster_dir = concepts_dir / "cluster_parent"
    cluster_dir.mkdir(parents=True, exist_ok=True)

    # Write parent concept
    filepath = cluster_dir / "parent-slug.md"
    content = """---
type: Concept
title: Parent Title
description: Parent Description
tags: []
related: []
confidence: 1.0
flagged: false
flagged_reason:
depth_level: 1
created_at: 2026-06-29T00:00:00Z
updated_at: 2026-06-29T00:00:00Z
---
# Parent Title

Parent body.
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    # Mock the LLM output to spawn a new concept referencing parent by title
    mock_generate.return_value = {
        "updated_body": "Updated parent body.",
        "new_concepts": [
            {
                "slug": "child-slug",
                "title": "Child Title",
                "description": "Child Description",
                "body": "## Section\nChild body.",
                "tags": ["child"],
                "related": ["Parent Title"],
                "depth_level": 2,
            }
        ],
    }

    from app.services.okf_service import expand_okf_concept
    expand_okf_concept(user_id, topic_id, okf_dir, "parent-slug", "some new data")

    # Assert new concept file has slug instead of title in related list
    child_file = cluster_dir / "child-slug.md"
    assert child_file.exists()

    with open(child_file, "r", encoding="utf-8") as f:
        child_content = f.read()

    assert "related: [\"parent-slug\"]" in child_content or 'related: ["parent-slug"]' in child_content
