import json
import os
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _load_staging(job_id: UUID) -> tuple[str, list]:
    """Load staged concepts from disk. Returns (path, concepts)."""
    staging_path = os.path.join(settings.DATA_DIR, "staging", f"{job_id}.json")
    if not os.path.exists(staging_path):
        raise HTTPException(status_code=404, detail="Staged concepts not found.")
    with open(staging_path, "r", encoding="utf-8") as f:
        return staging_path, json.load(f)


def _save_staging(path: str, concepts: list) -> None:
    """Persist staged concepts back to disk."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(concepts, f, indent=2)


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve status and progress of a background job.
    Enforces user isolation.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    return job


@router.get("/{job_id}/staged-concepts")
def get_staged_concepts(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the full list of staged concepts awaiting review."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    _, concepts = _load_staging(job_id)
    return concepts


@router.delete("/{job_id}/staged-concepts/{slug}")
def delete_staged_concept(
    job_id: UUID,
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a concept from the staging file by slug."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    staging_path, concepts = _load_staging(job_id)
    filtered = [c for c in concepts if c.get("slug") != slug]

    if len(filtered) == len(concepts):
        raise HTTPException(status_code=404, detail=f"Concept '{slug}' not found in staging.")

    _save_staging(staging_path, filtered)
    return {"status": "deleted", "slug": slug, "remaining": len(filtered)}


@router.post("/{job_id}/staged-concepts/{slug}/refine")
def refine_staged_concept(
    job_id: UUID,
    slug: str,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Use LLM to refine/deepen a specific concept in the staging file.
    Updates the staging JSON in-place and returns the updated body.
    """
    from app.services.okf_service import _generate_text_with_llm

    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    staging_path, concepts = _load_staging(job_id)
    concept = next((c for c in concepts if c.get("slug") == slug), None)
    if not concept:
        raise HTTPException(status_code=404, detail=f"Concept '{slug}' not found in staging.")

    user_prompt = request.get("prompt", "").strip()
    instruction = (
        user_prompt
        if user_prompt
        else "Expand and deepen this concept with more detail, examples, and structured sections."
    )

    refine_prompt = f"""You are an expert knowledge engineer refining an educational concept for a study portal.

Concept Title: {concept.get('title')}
Current Description: {concept.get('description')}

Current Body (Markdown):
{concept.get('body', '')}

User Refinement Request: {instruction}

Please rewrite and expand the concept body in Markdown format. The output should:
- Be more detailed and educational than the original
- Use clear ## section headings
- Include concrete examples where appropriate
- NOT include the main title (#) at the top
- Directly address the user's specific refinement request

Return ONLY the improved Markdown body, no extra commentary or code fences."""

    try:
        new_body = _generate_text_with_llm(refine_prompt)
        concept["body"] = new_body
        concept["flagged"] = False
        concept["flagged_reason"] = ""
        concept["confidence"] = min(1.0, float(concept.get("confidence", 0.7)) + 0.1)

        _save_staging(staging_path, concepts)
        return {"status": "success", "slug": slug, "updated_body": new_body}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refine concept: {e}")


@router.post("/{job_id}/staged-concepts/suggest")
def suggest_new_staged_concept(
    job_id: UUID,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Use LLM to generate a brand-new concept and append it to the staging file.
    """
    from app.services.okf_service import _generate_json_with_llm

    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    topic = request.get("topic", "").strip()
    if not topic:
        raise HTTPException(status_code=422, detail="'topic' field is required.")

    staging_path, concepts = _load_staging(job_id)
    existing_slugs = [c.get("slug") for c in concepts]
    existing_titles = [c.get("title") for c in concepts]

    suggest_prompt = f"""You are an expert knowledge engineer adding a new educational concept to a study topic.

Existing concepts already included: {', '.join(existing_titles)}

User's concept suggestion: "{topic}"

Generate ONE new concept object that is NOT a duplicate of any existing concept above.

Return ONLY a valid JSON object (not an array) with these exact keys:
- "slug": unique URL-friendly string (lowercase, hyphens, no spaces), must not match: {existing_slugs}
- "title": human-readable title string
- "description": one-line summary string
- "body": full explanation in Markdown format (use ## sections, no top-level # heading)
- "related": list of slugs from this list that relate: {existing_slugs}
- "tags": list of relevant tag strings
- "depth_level": integer 1, 2, or 3
- "confidence": float between 0.8 and 1.0
- "flagged": false
- "flagged_reason": ""
"""

    try:
        new_concept = _generate_json_with_llm(suggest_prompt)

        # Ensure it's a single dict, not an array
        if isinstance(new_concept, list):
            new_concept = new_concept[0]

        # Safety: ensure slug uniqueness
        base_slug = new_concept.get("slug", re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-"))
        final_slug = base_slug
        counter = 1
        while final_slug in existing_slugs:
            final_slug = f"{base_slug}-{counter}"
            counter += 1
        new_concept["slug"] = final_slug

        concepts.append(new_concept)
        _save_staging(staging_path, concepts)

        return {"status": "added", "concept": new_concept}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate concept: {e}")
