import os
import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.auth_dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.topic import Topic
from app.models.document import Document
from app.models.job import Job
from app.schemas.document import DocumentResponse
from app.core.config import settings
from app.workers.ingestion import process_document_task

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all documents for the current user in a specific topic.
    """
    # Enforce isolation
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == current_user.id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found."
        )
        
    return db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.topic_id == topic_id
    ).order_by(Document.ingested_at.desc()).all()

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    topic_id: UUID = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document (PDF, TXT, MD), save it to the local filesystem,
    create metadata entries, and trigger background parsing/ingestion.
    """
    # 1. Enforce isolation and topic scope
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == current_user.id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found or access denied."
        )
        
    # 2. Validate file extension
    filename = file.filename or "document"
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in [".pdf", ".txt", ".md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF, TXT, and MD files are allowed."
        )
        
    # 3. Validate file size (15MB limit)
    contents = await file.read()
    if len(contents) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 15MB."
        )
        
    # 4. Generate metadata & path
    document_id = uuid.uuid4()
    user_upload_dir = os.path.join(settings.UPLOADS_DIR, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)
    
    storage_path = os.path.join(user_upload_dir, f"{document_id}{ext}")
    
    # 5. Write file content to disk
    with open(storage_path, "wb") as f:
        f.write(contents)
        
    # Determine source type
    source_type = "upload_pdf" if ext == ".pdf" else "upload_text"
    
    # 6. Database entries
    doc_record = Document(
        id=document_id,
        user_id=current_user.id,
        topic_id=topic_id,
        source_type=source_type,
        storage_path=storage_path,
        original_filename=filename,
        status="pending"
    )
    
    job_record = Job(
        user_id=current_user.id,
        status="pending",
        task_type="document_ingestion",
        progress=0
    )
    
    db.add(doc_record)
    db.add(job_record)
    db.commit()
    db.refresh(doc_record)
    db.refresh(job_record)
    
    # 7. Register background worker task
    background_tasks.add_task(
        process_document_task,
        job_record.id,
        doc_record.id,
        current_user.id
    )
    
    return {
        "message": "File uploaded successfully. Processing started in background.",
        "document": doc_record,
        "job_id": job_record.id
    }


class RawTextIngestRequest(BaseModel):
    topic_id: UUID
    title: str = Field(..., max_length=255)
    content: str = Field(..., min_length=1)

class WebSearchIngestRequest(BaseModel):
    topic_id: UUID
    title: str = Field(..., max_length=255)
    syllabus: str = Field(..., max_length=1000)
    topics: str = Field(..., max_length=1000)


@router.post("/raw-text", status_code=status.HTTP_202_ACCEPTED)
async def ingest_raw_text(
    req: RawTextIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest a document from raw text content, save it to the local filesystem as a .txt file,
    create metadata entries, and trigger background parsing/ingestion.
    """
    # 1. Enforce isolation and topic scope
    topic = db.query(Topic).filter(Topic.id == req.topic_id, Topic.user_id == current_user.id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found or access denied."
        )

    # 2. Validate content size limit (15MB limit)
    content_bytes = req.content.encode("utf-8")
    if len(content_bytes) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content size exceeds the maximum limit of 15MB."
        )

    # 3. Generate metadata & path
    document_id = uuid.uuid4()
    user_upload_dir = os.path.join(settings.UPLOADS_DIR, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)

    storage_path = os.path.join(user_upload_dir, f"{document_id}.txt")

    # 4. Write content to disk
    with open(storage_path, "w", encoding="utf-8") as f:
        f.write(req.content)

    # 5. Database entries
    doc_record = Document(
        id=document_id,
        user_id=current_user.id,
        topic_id=req.topic_id,
        source_type="manual_topic_text",
        storage_path=storage_path,
        original_filename=req.title,
        status="pending"
    )

    job_record = Job(
        user_id=current_user.id,
        status="pending",
        task_type="document_ingestion",
        progress=0
    )

    db.add(doc_record)
    db.add(job_record)
    db.commit()
    db.refresh(doc_record)
    db.refresh(job_record)

    # 6. Register background worker task
    background_tasks.add_task(
        process_document_task,
        job_record.id,
        doc_record.id,
        current_user.id
    )

    return {
        "message": "Raw text ingested successfully. Processing started in background.",
        "document": doc_record,
        "job_id": job_record.id
    }


@router.post("/web-search", status_code=status.HTTP_202_ACCEPTED)
async def ingest_web_search(
    req: WebSearchIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest a document by simulating web search agent scraping, save it to the local filesystem as a .txt file,
    create metadata entries, and trigger background parsing/ingestion.
    """
    # 1. Enforce isolation and topic scope
    topic = db.query(Topic).filter(Topic.id == req.topic_id, Topic.user_id == current_user.id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found or access denied."
        )

    # 2. Build mock web parser corpus
    web_parsed_content = f"""Web Search Parser Agent (Placeholder Ingestion)
Document Title: {req.title}
Syllabus Requirements:
{req.syllabus}

Target Search Topics:
{req.topics}

---
Simulated Parser Agent Run:
- Initialized web agent search query for syllabus: "{req.title}"
- Parsed online resources (Wikipedia, official docs, textbooks) for the following topic list:
  {req.topics}
- Scraped relevant definitions, diagrams outlines, and detailed theoretical frameworks.
- Cleaned markdown text corpus assembled successfully for embedding.
- This is a functional placeholder corpus representing scraped content from web resources.
"""

    content_bytes = web_parsed_content.encode("utf-8")
    if len(content_bytes) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content size exceeds the maximum limit of 15MB."
        )

    # 3. Generate metadata & path
    document_id = uuid.uuid4()
    user_upload_dir = os.path.join(settings.UPLOADS_DIR, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)

    storage_path = os.path.join(user_upload_dir, f"{document_id}.txt")

    # 4. Write content to disk
    with open(storage_path, "w", encoding="utf-8") as f:
        f.write(web_parsed_content)

    # 5. Database entries
    doc_record = Document(
        id=document_id,
        user_id=current_user.id,
        topic_id=req.topic_id,
        source_type="web_scan",
        storage_path=storage_path,
        original_filename=req.title,
        status="pending"
    )

    job_record = Job(
        user_id=current_user.id,
        status="pending",
        task_type="document_ingestion",
        progress=0
    )

    db.add(doc_record)
    db.add(job_record)
    db.commit()
    db.refresh(doc_record)
    db.refresh(job_record)

    # 6. Register background worker task
    background_tasks.add_task(
        process_document_task,
        job_record.id,
        doc_record.id,
        current_user.id
    )

    return {
        "message": "Web search simulated successfully. Agent corpus created and queued.",
        "document": doc_record,
        "job_id": job_record.id
    }
