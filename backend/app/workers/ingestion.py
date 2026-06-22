import os
import uuid
import logging
from pypdf import PdfReader
from app.models.document import Document
from app.models.content_chunk import ContentChunk
from app.models.job import Job
from app.core.config import settings
from app.core.database import SessionLocal
from google import genai

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Splits text into chunks of roughly chunk_size characters with chunk_overlap overlap,
    without breaking words mid-character.
    """
    chunks = []
    if not text:
        return chunks
    
    # Normalize lines and spacing
    lines = [line.strip() for line in text.splitlines()]
    clean_text = "\n".join(line for line in lines if line)
    
    start = 0
    text_len = len(clean_text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # Adjust end to avoid splitting words
        if end < text_len:
            last_space = clean_text.rfind(" ", end - 100, end)
            if last_space != -1 and last_space > start:
                end = last_space
                
        chunk = clean_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        start = end - chunk_overlap
        if start >= text_len - chunk_overlap:
            break
        if start < 0:
            start = 0
            
    return chunks

def get_embeddings(chunks: list[str]) -> list[list[float]]:
    """
    Call Gemini API to generate embeddings for list of chunks.
    Falls back to mock embeddings in test environment or if API key is not configured.
    """
    is_mock = (
        not settings.GEMINI_API_KEY or 
        settings.GEMINI_API_KEY == "your-gemini-api-key-here" or
        settings.APP_ENV == "test"
    )
    
    if is_mock:
        logger.warning("Using mock embeddings (no valid GEMINI_API_KEY or in test).")
        return [[0.1 * (idx % 10)] * settings.EMBEDDING_DIMENSION for idx in range(len(chunks))]
        
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        embeddings = []
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=batch
            )
            for emb in response.embeddings:
                embeddings.append(emb.values)
        return embeddings
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}. Falling back to mock embeddings in local/debug environment.")
        if settings.APP_ENV == "local" or settings.DEBUG:
            return [[0.1 * (idx % 10)] * settings.EMBEDDING_DIMENSION for idx in range(len(chunks))]
        raise e

def process_document_task(job_id: uuid.UUID, document_id: uuid.UUID, user_id: uuid.UUID, db=None) -> None:
    """
    Background worker job for processing an uploaded document:
    1. Reads & parses document (PDF or Text/Markdown).
    2. Segments into text chunks.
    3. Calls Gemini Embeddings API.
    4. Writes results to the database and updates job state.
    """
    is_external_db = db is not None
    if not is_external_db:
        db = SessionLocal()
        
    try:
        # Fetch Job and Document
        job = db.query(Job).filter(Job.id == job_id).first()
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        if not job or not doc:
            logger.error(f"Job {job_id} or Document {document_id} not found in DB.")
            return
            
        job.status = "running"
        job.progress = 10
        doc.status = "parsing"
        db.commit()
        
        # Check storage file path
        if not doc.storage_path or not os.path.exists(doc.storage_path):
            raise FileNotFoundError(f"Uploaded file not found at {doc.storage_path}")
            
        # Extract text from file
        job.progress = 30
        db.commit()
        
        _, ext = os.path.splitext(doc.storage_path)
        ext = ext.lower()
        
        if ext == ".pdf":
            reader = PdfReader(doc.storage_path)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        else:
            with open(doc.storage_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                
        if not text.strip():
            raise ValueError("No extractable text found in document.")
            
        # Chunk text
        job.progress = 50
        db.commit()
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("Document yielded zero text chunks.")
            
        # Generate embeddings
        job.progress = 70
        db.commit()
        embeddings = get_embeddings(chunks)
        
        # Save chunks and vectors
        job.progress = 90
        db.commit()
        
        for idx, (chunk_text_content, emb_vector) in enumerate(zip(chunks, embeddings)):
            chunk = ContentChunk(
                document_id=doc.id,
                user_id=user_id,
                topic_id=doc.topic_id,
                chunk_text=chunk_text_content,
                embedding=emb_vector,
                chunk_index=idx
            )
            db.add(chunk)
            
        doc.status = "parsed"
        job.status = "completed"
        job.progress = 100
        db.commit()
        logger.info(f"Successfully processed document {document_id} (job {job_id}).")
        
    except Exception as e:
        db.rollback()
        logger.exception(f"Exception encountered during document processing (job {job_id}): {e}")
        try:
            # Refresh session and set statuses to failed
            job = db.query(Job).filter(Job.id == job_id).first()
            doc = db.query(Document).filter(Document.id == document_id).first()
            if job:
                job.status = "failed"
                job.message = str(e)
                job.progress = 100
            if doc:
                doc.status = "failed"
            db.commit()
        except Exception as db_err:
            logger.error(f"Failed to write error state to database: {db_err}")
    finally:
        if not is_external_db:
            db.close()

