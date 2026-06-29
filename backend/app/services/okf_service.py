import datetime
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.llm_service import get_llm_client

logger = logging.getLogger(__name__)

# --- LLM Prompts ---

CONCEPT_EXTRACTION_PROMPT = """You are an expert knowledge engineer.
Your task is to synthesize raw web search data into a structured Open Knowledge Format (OKF).
Extract the core concepts from the retrieved source material based on the syllabus.
For each distinct concept, you will output a structured object containing the concept title, description, markdown body, and related concepts.

Title: {title}
Syllabus / Learning Objectives:
{syllabus}

Retrieved Source Material:
{sources_text}

Output format:
You must return ONLY a JSON array of objects, where each object has the following keys:
- "slug": a unique URL-friendly string identifier (e.g., "arrays", "hash-maps")
- "title": a human-readable title (e.g., "Arrays")
- "description": a one-line summary of the concept
- "body": the full explanation in Markdown format. Use Markdown headings (##) for sections. Do NOT include the main title (#) inside the body, start directly with ## sections or paragraphs.
- "related": a list of string slugs for related concepts extracted in this batch
- "tags": a list of relevant tags (e.g., ["data-structures", "memory"])
- "depth_level": integer indicating depth (1=surface, 2=intermediate, 3=deep)

Ensure the content directly addresses the syllabus and is highly educational.
"""

CONCEPT_VALIDATION_PROMPT = """You are a rigorous quality-assurance agent.
Review the following list of extracted concepts. Your job is to assign a confidence score (0.0 to 1.0) to each concept and flag any that are ambiguous, incomplete, or poorly supported by standard knowledge.

Concepts to review:
{concepts_json}

Rules for flagging:
- If a concept has very little detail, flag it.
- If a concept seems contradictory or factually suspicious, flag it.
- If a concept lacks proper structure, flag it.

Output format:
You must return ONLY a JSON array of objects, where each object has:
- "slug": the exact slug from the input
- "confidence": float between 0.0 and 1.0
- "flagged": boolean (true if it needs human review based on the rules above or if confidence < 0.7)
- "flagged_reason": string explaining why it was flagged (empty string if flagged is false)
"""


def _generate_json_with_llm(
    prompt: str, is_mock: bool = False, mock_response: list | dict = None
) -> Any:
    """Helper to generate structured JSON from LLM."""
    if is_mock:
        return mock_response or []

    provider = settings.LLM_PROVIDER.lower().strip()
    max_retries = 3

    for attempt in range(max_retries):
        try:
            if provider == "gemini":
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                model_name = settings.LLM_MODEL or "gemini-3.1-flash-lite"
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                raw = response.text.strip()
            elif provider in ("openai", "lmstudio"):
                client = get_llm_client()
                model_name = settings.LLM_MODEL
                if not model_name:
                    model_name = "gpt-4o-mini" if provider == "openai" else "local-model"

                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Output ONLY a valid JSON object or array. No markdown formatting blocks.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"} if provider == "openai" else None,
                )
                raw = response.choices[0].message.content.strip()
                # Clean markdown JSON blocks if present
                if raw.startswith("```json"):
                    raw = raw.removeprefix("```json").removesuffix("```").strip()
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")

            parsed = json.loads(raw)
            if isinstance(parsed, dict) and len(parsed.keys()) == 1 and "concepts" in parsed:
                return list(parsed.values())[0]
            if isinstance(parsed, dict) and "reviews" in parsed:
                return parsed["reviews"]
            return parsed

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to generate JSON from LLM: {e}")
                raise e


def _generate_text_with_llm(prompt: str, is_mock: bool = False, mock_response: str = None) -> str:
    """Helper to generate raw text (markdown) from LLM."""
    if is_mock:
        return mock_response or "Mock markdown content."

    provider = settings.LLM_PROVIDER.lower().strip()
    max_retries = 3

    for attempt in range(max_retries):
        try:
            if provider == "gemini":
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                model_name = settings.LLM_MODEL or "gemini-3.1-flash-lite"
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text.strip()
            elif provider in ("openai", "lmstudio"):
                client = get_llm_client()
                model_name = settings.LLM_MODEL
                if not model_name:
                    model_name = "gpt-4o-mini" if provider == "openai" else "local-model"

                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful knowledge assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                return response.choices[0].message.content.strip()
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to generate text from LLM: {e}")
                raise e


def generate_okf_concepts(title: str, syllabus: str, query_data: dict[str, str]) -> list[dict]:
    """
    LLM call: raw scrape data -> list of OKF concept dicts.
    """
    is_mock = settings.APP_ENV == "test"

    sources_text = ""
    for query, text in query_data.items():
        sources_text += f"\n--- Query Topic: {query} ---\n{text[:5000]}\n"

    prompt = CONCEPT_EXTRACTION_PROMPT.format(
        title=title, syllabus=syllabus, sources_text=sources_text
    )

    mock_resp = [
        {
            "slug": "mock-concept",
            "title": "Mock Concept",
            "description": "A mock concept for testing.",
            "body": "## Introduction\nThis is a mock concept.",
            "related": [],
            "tags": ["mock"],
            "depth_level": 1,
        }
    ]

    return _generate_json_with_llm(prompt, is_mock, mock_resp)


def validate_okf_concepts(concepts: list[dict]) -> list[dict]:
    """
    LLM self-review: assign confidence scores, set flagged=true on low-confidence.
    """
    is_mock = settings.APP_ENV == "test"
    if not concepts:
        return []

    # Strip the heavy bodies to save tokens during validation, just send the structure
    stripped_concepts = [
        {
            "slug": c.get("slug"),
            "title": c.get("title"),
            "description": c.get("description"),
            "body_length": len(c.get("body", "")),
        }
        for c in concepts
    ]

    prompt = CONCEPT_VALIDATION_PROMPT.format(concepts_json=json.dumps(stripped_concepts, indent=2))

    mock_resp = [
        {
            "slug": c.get("slug"),
            "confidence": 0.9,
            "flagged": False,
            "flagged_reason": "",
        }
        for c in concepts
    ]

    validation_results = _generate_json_with_llm(prompt, is_mock, mock_resp)

    # Merge validation results back into the original concepts
    validation_map = {res.get("slug"): res for res in validation_results if isinstance(res, dict)}

    validated_concepts = []
    for concept in concepts:
        slug = concept.get("slug")
        v_data = validation_map.get(slug, {})
        concept["confidence"] = v_data.get("confidence", 0.5)
        concept["flagged"] = v_data.get("flagged", True)
        concept["flagged_reason"] = v_data.get("flagged_reason", "Validation data missing.")
        validated_concepts.append(concept)

    return validated_concepts


def _cluster_concepts(concepts: list[dict]) -> dict[str, list[dict]]:
    """Groups concepts into connected components."""
    adj = {c["slug"]: set() for c in concepts}
    for c in concepts:
        slug = c["slug"]
        for target in c.get("related", []):
            if target in adj:
                adj[slug].add(target)
                adj[target].add(slug)

    visited = set()
    clusters = {}
    for c in concepts:
        slug = c["slug"]
        if slug not in visited:
            cluster_nodes = []
            queue = [slug]
            visited.add(slug)
            while queue:
                curr = queue.pop(0)
                cluster_nodes.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            cluster_concepts = [x for x in concepts if x["slug"] in cluster_nodes]
            hub = max(cluster_nodes, key=lambda n: len(adj[n]))
            clusters[f"cluster_{hub}"] = cluster_concepts

    return clusters


def write_okf_concepts(user_id: uuid.UUID, topic_id: uuid.UUID, concepts: list[dict], okf_dir: str):
    """
    Write approved concept .md files into clustered directories + index.md + initial log.md entry.
    """
    base_dir = Path(okf_dir)
    concepts_dir = base_dir / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    clusters = _cluster_concepts(concepts)
    master_index_content = f"# OKF Concept Index\n\nGenerated on {timestamp}\n\n## Clusters\n"

    for cluster_name, cluster_concepts in clusters.items():
        cluster_dir = concepts_dir / cluster_name
        cluster_dir.mkdir(parents=True, exist_ok=True)

        cluster_index_content = (
            f"# Cluster: {cluster_name}\n\nGenerated on {timestamp}\n\n## Concepts\n"
        )

        for concept in cluster_concepts:
            slug = concept["slug"]
            title = concept.get("title", slug)
            desc = concept.get("description", "")
            tags = json.dumps(concept.get("tags", []))
            related = json.dumps(concept.get("related", []))
            confidence = concept.get("confidence", 1.0)
            flagged = str(concept.get("flagged", False)).lower()
            reason = concept.get("flagged_reason", "")
            depth = concept.get("depth_level", 1)
            body = concept.get("body", "")

            frontmatter = f"""---
type: Concept
title: {title}
description: {desc}
tags: {tags}
related: {related}
confidence: {confidence}
flagged: {flagged}
flagged_reason: {reason}
depth_level: {depth}
created_at: {timestamp}
updated_at: {timestamp}
---
# {title}

{body}
"""
            filepath = cluster_dir / f"{slug}.md"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(frontmatter)

            cluster_index_content += f"- [{title}]({slug}.md): {desc}\n"

        with open(cluster_dir / "index.md", "w", encoding="utf-8") as f:
            f.write(cluster_index_content)

        master_index_content += f"- [{cluster_name}](concepts/{cluster_name}/index.md): {len(cluster_concepts)} concepts\n"

    # Write master index.md
    index_path = base_dir / "index.md"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(master_index_content)

    # Write/append log.md
    append_okf_log(user_id, topic_id, "Generated initial OKF concepts from web search.", okf_dir)


def chunk_from_okf(concept_files: list[str]) -> list[tuple[str, str]]:
    """
    Extract text chunks from OKF files — one chunk per ## section.
    Returns list of (concept_path, chunk_text).
    """
    chunks = []
    for filepath in concept_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Split frontmatter
            parts = content.split("---")
            if len(parts) >= 3:
                body = "---".join(parts[2:]).strip()
            else:
                body = content.strip()

            # Split by ##
            sections = re.split(r"\n##\s+", body)

            # The first part is everything before the first ## (e.g. # Title and intro)
            if sections[0].strip():
                chunks.append((filepath, sections[0].strip()))

            # Subsequent sections
            for section in sections[1:]:
                if section.strip():
                    chunks.append((filepath, "## " + section.strip()))

        except Exception as e:
            logger.error(f"Failed to chunk OKF file {filepath}: {e}")

    return chunks


def load_okf_index(user_id: uuid.UUID, topic_id: uuid.UUID, okf_dir: str) -> dict:
    """
    Parse all concept frontmatter recursively in clusters -> graph JSON.
    """
    base_dir = Path(okf_dir)
    concepts_dir = base_dir / "concepts"

    nodes = []
    edges = []

    if concepts_dir.exists():
        for file in concepts_dir.rglob("*.md"):
            if file.name == "index.md":
                continue
            try:
                slug = file.stem
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()

                parts = content.split("---")
                if len(parts) >= 3:
                    frontmatter_text = parts[1]

                    # Manual basic parsing
                    title_match = re.search(r"title:\s*(.*)", frontmatter_text)
                    desc_match = re.search(r"description:\s*(.*)", frontmatter_text)
                    related_match = re.search(
                        r"related:\s*(\[.*?\])", frontmatter_text, flags=re.DOTALL
                    )
                    tags_match = re.search(r"tags:\s*(\[.*?\])", frontmatter_text, flags=re.DOTALL)

                    title = title_match.group(1).strip() if title_match else slug
                    desc = desc_match.group(1).strip() if desc_match else ""

                    try:
                        related = json.loads(related_match.group(1)) if related_match else []
                    except:
                        related = []

                    try:
                        tags = json.loads(tags_match.group(1)) if tags_match else []
                    except:
                        tags = []

                    cluster_name = file.parent.name
                    nodes.append(
                        {
                            "id": slug,
                            "title": title,
                            "description": desc,
                            "tags": tags,
                            "path": f"concepts/{cluster_name}/{file.name}",
                        }
                    )

                    for target in related:
                        edges.append({"source": slug, "target": target})
            except Exception as e:
                logger.error(f"Failed to parse OKF frontmatter for {file}: {e}")

    return {"nodes": nodes, "edges": edges}


def expand_okf_concept(
    user_id: uuid.UUID, topic_id: uuid.UUID, okf_dir: str, slug: str, new_raw_data: str
) -> tuple[str, list[str]]:
    """
    Merge or append to an existing concept file using an LLM to rewrite the body seamlessly,
    and potentially spawn new concepts. Returns (updated_body, list_of_all_modified_slugs).
    """
    is_mock = settings.APP_ENV == "test"
    base_dir = Path(okf_dir)

    # Find the concept file in any cluster directory
    matches = list(base_dir.glob(f"concepts/*/{slug}.md"))
    if not matches:
        # Fallback for older flat structure
        matches = list(base_dir.glob(f"concepts/{slug}.md"))
        if not matches:
            raise ValueError(f"Concept {slug} not found in any cluster.")
    filepath = matches[0]
    cluster_dir = filepath.parent
    # If the parent is literally "concepts", it's an unclustered legacy doc.
    cluster_name = cluster_dir.name if cluster_dir.name != "concepts" else None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---")
    if len(parts) >= 3:
        frontmatter_text = parts[1]
        body = "---".join(parts[2:]).strip()
    else:
        frontmatter_text = ""
        body = content.strip()

    prompt = f"""You are an expert knowledge engineer. Your task is to update and expand an existing educational concept document with new information.
If the new information introduces entirely new dense concepts, spawn them as new concepts.

Existing Concept Body:
{body}

New Information to Weave In:
{new_raw_data}

Output format:
You must return ONLY a JSON object with two keys:
- "updated_body": The newly rewritten markdown body for this concept (do not include title headers or YAML).
- "new_concepts": A list of objects for any new concepts spawned (each containing "slug", "title", "description", "body", "tags", "related", "depth_level"). Leave empty if no new concepts are needed.
"""

    mock_resp = {
        "updated_body": body + f"\n\n## Added Information\n{new_raw_data}",
        "new_concepts": [],
    }

    result = _generate_json_with_llm(prompt, is_mock=is_mock, mock_response=mock_resp)

    updated_body = result.get("updated_body", "")
    new_concepts = result.get("new_concepts", [])

    # Update related array in parent frontmatter if new concepts were created
    new_slugs = [c["slug"] for c in new_concepts]

    related_match = re.search(r"related:\s*(\[.*?\])", frontmatter_text, flags=re.DOTALL)
    if related_match:
        try:
            related_list = json.loads(related_match.group(1))
            related_list.extend(new_slugs)
            related_list = list(set(related_list))
            frontmatter_text = frontmatter_text.replace(
                related_match.group(0), f"related: {json.dumps(related_list)}"
            )
        except:
            pass

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Overwrite the parent file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"---\n{frontmatter_text}\n---\n# {filepath.stem}\n\n{updated_body}\n")

    # Generate new concept files in the same cluster
    for nc in new_concepts:
        n_slug = nc["slug"]
        n_title = nc.get("title", n_slug)
        n_desc = nc.get("description", "")
        n_tags = json.dumps(nc.get("tags", []))
        n_related = json.dumps(nc.get("related", [slug]))
        n_depth = nc.get("depth_level", 2)
        n_body = nc.get("body", "")

        n_frontmatter = f"""---
type: Concept
title: {n_title}
description: {n_desc}
tags: {n_tags}
related: {n_related}
confidence: 1.0
flagged: false
flagged_reason: 
depth_level: {n_depth}
created_at: {timestamp}
updated_at: {timestamp}
---
# {n_title}

{n_body}
"""
        with open(cluster_dir / f"{n_slug}.md", "w", encoding="utf-8") as f:
            f.write(n_frontmatter)

        # Append to cluster index (or base index if legacy flat structure)
        index_file = cluster_dir / "index.md" if cluster_name is not None else base_dir / "index.md"
        with open(index_file, "a", encoding="utf-8") as f:
            f.write(f"- [{n_title}]({n_slug}.md): {n_desc}\n")

    append_okf_log(
        user_id,
        topic_id,
        f"Manually deepened concept: {slug}. Spawned {len(new_concepts)} new concepts.",
        okf_dir,
    )

    all_modified_slugs = [slug] + new_slugs
    return updated_body, all_modified_slugs


def append_okf_log(user_id: uuid.UUID, topic_id: uuid.UUID, event: str, okf_dir: str):
    """
    Write append-only log entry to log.md.
    """
    log_path = Path(okf_dir) / "log.md"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry = f"- **{timestamp}**: {event}\n"

    mode = "a" if log_path.exists() else "w"
    try:
        with open(log_path, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write("# OKF Event Log\n\n")
            f.write(entry)
    except Exception as e:
        logger.error(f"Failed to write to OKF log {log_path}: {e}")
