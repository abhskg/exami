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
