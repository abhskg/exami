import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth_dependencies import get_current_user
from app.models.document import Document
from app.models.user import User
from app.schemas.knowledge import ConceptReviewRequest, DeepenRequest, KnowledgeGraph
from app.services.okf_service import load_okf_index
from app.workers.ingestion import finalize_web_search_task

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/{topic_id}/graph", response_model=KnowledgeGraph)
def get_knowledge_graph(
    topic_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(Document.topic_id == topic_id, Document.user_id == current_user.id)
        .first()
    )

    if not doc or not doc.okf_directory_path:
        raise HTTPException(status_code=404, detail="Knowledge graph not found for this topic")

    try:
        graph = load_okf_index(current_user.id, topic_id, doc.okf_directory_path)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load graph: {e}")


@router.get("/{topic_id}/concept/{slug}")
def get_concept_body(
    topic_id: uuid.UUID,
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(Document.topic_id == topic_id, Document.user_id == current_user.id)
        .first()
    )

    if not doc or not doc.okf_directory_path:
        raise HTTPException(status_code=404, detail="Knowledge directory not found")

    filepath = os.path.join(doc.okf_directory_path, "concepts", f"{slug}.md")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Concept file not found")

    with open(filepath, "r", encoding="utf-8") as f:
        return {"body": f.read()}


@router.post("/{topic_id}/review")
def review_concepts(
    topic_id: uuid.UUID,
    request: ConceptReviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(
            Document.id == request.document_id,
            Document.topic_id == topic_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    background_tasks.add_task(
        finalize_web_search_task,
        request.job_id,
        request.document_id,
        current_user.id,
        request.approved_concepts,
    )

    return {"status": "accepted", "message": "Finalizing OKF concepts in background."}


from app.services.okf_service import expand_okf_concept


@router.post("/{topic_id}/concept/{slug}/deepen")
def deepen_concept(
    topic_id: uuid.UUID,
    slug: str,
    request: DeepenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(Document.topic_id == topic_id, Document.user_id == current_user.id)
        .first()
    )

    if not doc or not doc.okf_directory_path:
        raise HTTPException(status_code=404, detail="Knowledge directory not found")

    try:
        updated_content = expand_okf_concept(
            current_user.id, topic_id, doc.okf_directory_path, slug, request.new_raw_data
        )
        return {
            "status": "success",
            "message": "Concept expanded",
            "updated_content": updated_content,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to expand concept: {e}")
