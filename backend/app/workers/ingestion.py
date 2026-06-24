import logging
import os
import uuid

from pypdf import PdfReader

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.content_chunk import ContentChunk
from app.models.document import Document
from app.models.job import Job

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
    Call centralized llm_service to generate embeddings for a list of chunks.
    Processes in batches of 10 to respect rate limits.
    """
    import time

    from app.services import llm_service

    embeddings = []
    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_embs = llm_service.embed_text(batch)
        embeddings.extend(batch_embs)

        # Respect rate limits on multiple batches
        if i + batch_size < len(chunks):
            time.sleep(1.0)

    return embeddings


def process_document_task(
    job_id: uuid.UUID, document_id: uuid.UUID, user_id: uuid.UUID, db=None
) -> None:
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
                chunk_index=idx,
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


def process_web_search_task(
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    syllabus: str,
    topics: str,
    db=None,
) -> None:
    """
    Background worker job for running web search parser agents:
    1. Parses topics into individual target queries.
    2. Searches Wikipedia/scrapes DuckDuckGo search results for each topic.
    3. Synthesizes scraped documents using LLM.
    4. Writes synthesized text to disk.
    5. Segments compiled guide into semantic chunks.
    6. Calls Embeddings API and saves to database.
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

        # Parse topics into separate query targets
        queries = []
        if "," in topics:
            queries = [q.strip() for q in topics.split(",") if q.strip()]
        elif "\n" in topics:
            queries = [q.strip() for q in topics.split("\n") if q.strip()]
        else:
            queries = [topics.strip()]

        # Fallback to title if queries is empty
        if not queries or all(not q for q in queries):
            queries = [title]

        # Limit to top 5 queries to avoid overly long executions
        queries = queries[:5]
        total_queries = len(queries)

        from app.services.llm_service import synthesize_search_results
        from app.services.search_service import research_topic

        query_data = {}
        for idx, q in enumerate(queries):
            # Update progress during scraping (from 10% to 60%)
            percent = int(10 + (idx / total_queries) * 50)
            job.progress = percent
            job.message = f"Web scraping for topic: '{q}'..."
            db.commit()

            logger.info(f"Researching topic query '{q}' ({idx+1}/{total_queries}) for job {job_id}")
            text_result = research_topic(q, syllabus)
            if text_result:
                query_data[q] = text_result

        # Synthesize into unified guide
        job.progress = 65
        job.message = "Synthesizing research results into study guide..."
        db.commit()

        synthesized_guide = synthesize_search_results(title, syllabus, query_data)

        # Ensure directory exists and write compiled guide to storage path
        job.progress = 75
        job.message = "Writing compiled document to disk..."
        db.commit()

        user_upload_dir = os.path.dirname(doc.storage_path)
        os.makedirs(user_upload_dir, exist_ok=True)
        with open(doc.storage_path, "w", encoding="utf-8") as f:
            f.write(synthesized_guide)

        # Segment into chunks
        job.progress = 80
        job.message = "Chunking synthesized document..."
        db.commit()

        chunks = chunk_text(synthesized_guide)
        if not chunks:
            raise ValueError("Synthesized document yielded zero text chunks.")

        # Generate embeddings
        job.progress = 85
        job.message = "Generating vector embeddings..."
        db.commit()

        embeddings = get_embeddings(chunks)

        # Save chunks and vectors
        job.progress = 95
        job.message = "Saving segments to database..."
        db.commit()

        for idx, (chunk_text_content, emb_vector) in enumerate(zip(chunks, embeddings)):
            chunk = ContentChunk(
                document_id=doc.id,
                user_id=user_id,
                topic_id=doc.topic_id,
                chunk_text=chunk_text_content,
                embedding=emb_vector,
                chunk_index=idx,
            )
            db.add(chunk)

        doc.status = "parsed"
        job.status = "completed"
        job.progress = 100
        job.message = "Completed compiling and vectorizing."
        db.commit()
        logger.info(f"Successfully processed web search document {document_id} (job {job_id}).")

    except Exception as e:
        db.rollback()
        logger.exception(f"Exception encountered during web search processing (job {job_id}): {e}")
        try:
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
