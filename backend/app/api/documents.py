import logging
import os
import uuid
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document
from app.models.content_chunk import ContentChunk
from app.models.job import Job
from app.models.topic import Topic
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentUpdateRequest,
    ContentChunkResponse,
    ChunkUpdateRequest,
)
from app.workers.ingestion import process_document_task
from app.services.llm_service import embed_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all documents for the current user in a specific topic.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) listing documents for topic {topic_id}"
    )

    # Enforce isolation
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == current_user.id).first()
    if not topic:
        logger.warning(
            f"List documents failed: Topic {topic_id} not found or access denied for User {current_user.id}"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.topic_id == topic_id)
        .order_by(Document.ingested_at.desc())
        .all()
    )
    logger.debug(f"Retrieved {len(docs)} documents for topic {topic_id}")
    return docs


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    topic_id: UUID = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document (PDF, TXT, MD), save it to the local filesystem,
    create metadata entries, and trigger background parsing/ingestion.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) uploading document '{file.filename}' for topic {topic_id}"
    )

    # 1. Enforce isolation and topic scope
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == current_user.id).first()
    if not topic:
        logger.warning(
            f"Upload rejected: Topic {topic_id} not found or access denied for User {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found or access denied.",
        )

    # 2. Validate file extension
    filename = file.filename or "document"
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in [".pdf", ".txt", ".md"]:
        logger.warning(f"Upload rejected: Unsupported extension '{ext}' for file '{filename}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF, TXT, and MD files are allowed.",
        )

    # 3. Validate file size (settings.MAX_FILE_SIZE_MB limit)
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        logger.warning(
            f"Upload rejected: File size {len(contents)} bytes exceeds the {settings.MAX_FILE_SIZE_MB}MB limit for '{filename}'"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the maximum limit of {settings.MAX_FILE_SIZE_MB}MB.",
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
        status="pending",
    )

    job_record = Job(
        user_id=current_user.id,
        status="pending",
        task_type="document_ingestion",
        progress=0,
    )

    db.add(doc_record)
    db.add(job_record)
    db.commit()
    db.refresh(doc_record)
    db.refresh(job_record)

    logger.info(
        f"File uploaded. Document ID: {document_id}. Registered background ingestion Job ID: {job_record.id}"
    )

    # 7. Register background worker task
    background_tasks.add_task(process_document_task, job_record.id, doc_record.id, current_user.id)

    return {
        "message": "File uploaded successfully. Processing started in background.",
        "document": doc_record,
        "job_id": job_record.id,
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
    current_user: User = Depends(get_current_user),
):
    """
    Ingest a document from raw text content, save it to the local filesystem as a .txt file,
    create metadata entries, and trigger background parsing/ingestion.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) ingesting raw text: '{req.title}' for topic {req.topic_id}"
    )

    # 1. Enforce isolation and topic scope
    topic = (
        db.query(Topic).filter(Topic.id == req.topic_id, Topic.user_id == current_user.id).first()
    )
    if not topic:
        logger.warning(
            f"Raw text ingestion rejected: Topic {req.topic_id} not found or access denied for User {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found or access denied.",
        )

    # 2. Validate content size limit (settings.MAX_FILE_SIZE_MB limit)
    content_bytes = req.content.encode("utf-8")
    if len(content_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        logger.warning(
            f"Raw text ingestion rejected: Size {len(content_bytes)} bytes exceeds the {settings.MAX_FILE_SIZE_MB}MB limit for topic {req.topic_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content size exceeds the maximum limit of {settings.MAX_FILE_SIZE_MB}MB.",
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
        status="pending",
    )

    job_record = Job(
        user_id=current_user.id,
        status="pending",
        task_type="document_ingestion",
        progress=0,
    )

    db.add(doc_record)
    db.add(job_record)
    db.commit()
    db.refresh(doc_record)
    db.refresh(job_record)

    logger.info(
        f"Raw text document created. Document ID: {document_id}. Registered background ingestion Job ID: {job_record.id}"
    )

    # 6. Register background worker task
    background_tasks.add_task(process_document_task, job_record.id, doc_record.id, current_user.id)

    return {
        "message": "Raw text ingested successfully. Processing started in background.",
        "document": doc_record,
        "job_id": job_record.id,
    }


@router.post("/web-search", status_code=status.HTTP_202_ACCEPTED)
async def ingest_web_search(
    req: WebSearchIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ingest a document by simulating web search agent scraping, save it to the local filesystem as a .txt file,
    create metadata entries, and trigger background parsing/ingestion.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) triggering simulated web search parser: '{req.title}' for topic {req.topic_id}"
    )

    # 1. Enforce isolation and topic scope
    topic = (
        db.query(Topic).filter(Topic.id == req.topic_id, Topic.user_id == current_user.id).first()
    )
    if not topic:
        logger.warning(
            f"Web search ingestion rejected: Topic {req.topic_id} not found or access denied for User {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found or access denied.",
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
    if len(content_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        logger.warning(
            f"Web search ingestion rejected: Corpus size {len(content_bytes)} bytes exceeds {settings.MAX_FILE_SIZE_MB}MB for topic {req.topic_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content size exceeds the maximum limit of {settings.MAX_FILE_SIZE_MB}MB.",
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
        status="pending",
    )

    job_record = Job(
        user_id=current_user.id,
        status="pending",
        task_type="document_ingestion",
        progress=0,
    )

    db.add(doc_record)
    db.add(job_record)
    db.commit()
    db.refresh(doc_record)
    db.refresh(job_record)

    logger.info(
        f"Web scan simulated document created. Document ID: {document_id}. Registered background ingestion Job ID: {job_record.id}"
    )

    # 6. Register background worker task
    background_tasks.add_task(process_document_task, job_record.id, doc_record.id, current_user.id)

    return {
        "message": "Web search simulated successfully. Agent corpus created and queued.",
        "document": doc_record,
        "job_id": job_record.id,
    }


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: UUID,
    payload: DocumentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rename a document.
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    
    doc.original_filename = payload.original_filename
    db.commit()
    db.refresh(doc)
    logger.info(f"User {current_user.email} renamed document {document_id} to '{payload.original_filename}'")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a document from DB (cascades to chunks) and delete physical file.
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    
    # Try deleting the physical file
    if doc.storage_path and os.path.exists(doc.storage_path):
        try:
            os.remove(doc.storage_path)
            logger.info(f"Deleted physical file: {doc.storage_path}")
        except Exception as e:
            logger.error(f"Failed to delete physical file {doc.storage_path}: {e}")
            
    db.delete(doc)
    db.commit()
    logger.info(f"User {current_user.email} deleted document {document_id} and all related chunks.")
    return {"message": "Document deleted successfully."}


@router.get("/{document_id}/chunks", response_model=list[ContentChunkResponse])
def list_document_chunks(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List content chunks for a specific document.
    """
    # Enforce isolation
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        
    chunks = db.query(ContentChunk).filter(
        ContentChunk.document_id == document_id,
        ContentChunk.user_id == current_user.id
    ).order_by(ContentChunk.chunk_index.asc()).all()
    
    return chunks


@router.put("/chunks/{chunk_id}", response_model=ContentChunkResponse)
def update_chunk(
    chunk_id: UUID,
    payload: ChunkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update content chunk text and re-generate pgvector embedding.
    """
    chunk = db.query(ContentChunk).filter(
        ContentChunk.id == chunk_id,
        ContentChunk.user_id == current_user.id
    ).first()
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found.")
        
    chunk.chunk_text = payload.chunk_text
    
    # Regenerate embedding
    try:
        embeddings = embed_text([payload.chunk_text])
        if embeddings and len(embeddings) > 0:
            chunk.embedding = embeddings[0]
            logger.info(f"Regenerated vector embedding for chunk {chunk_id}")
    except Exception as e:
        logger.error(f"Error regenerating embedding during chunk update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate embedding: {str(e)}"
        )
        
    db.commit()
    db.refresh(chunk)
    return chunk


@router.delete("/chunks/{chunk_id}", status_code=status.HTTP_200_OK)
def delete_chunk(
    chunk_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a single content chunk.
    """
    chunk = db.query(ContentChunk).filter(
        ContentChunk.id == chunk_id,
        ContentChunk.user_id == current_user.id
    ).first()
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found.")
        
    db.delete(chunk)
    db.commit()
    logger.info(f"User {current_user.email} deleted chunk {chunk_id}")
    return {"message": "Chunk deleted successfully."}
