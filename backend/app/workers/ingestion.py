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

        from app.services.okf_service import generate_okf_concepts, validate_okf_concepts
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

        # Generate OKF Concepts
        job.progress = 65
        job.message = "Structuring research results into OKF concepts..."
        db.commit()

        concepts = generate_okf_concepts(title, syllabus, query_data)

        # Validate OKF Concepts
        job.progress = 75
        job.message = "Validating extracted concepts..."
        db.commit()

        validated_concepts = validate_okf_concepts(concepts)

        # Write to staging JSON file tied to job_id
        staging_dir = os.path.join(settings.DATA_DIR, "staging")
        os.makedirs(staging_dir, exist_ok=True)
        staging_path = os.path.join(staging_dir, f"{job_id}.json")

        import json

        with open(staging_path, "w", encoding="utf-8") as f:
            json.dump(validated_concepts, f, indent=2)

        # Set job state to awaiting_review
        job.status = "awaiting_review"
        job.progress = 85
        job.message = "Awaiting user review of extracted concepts."
        db.commit()
        logger.info(f"Staged {len(validated_concepts)} OKF concepts for review (job {job_id}).")

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


def finalize_web_search_task(
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    approved_concepts: list[dict],
    db=None,
) -> None:
    """
    Background worker job to finalize OKF concepts after user review:
    1. Writes approved OKF concept files to disk.
    2. Chunks text from the OKF semantic boundaries.
    3. Generates embeddings and writes to pgvector.
    """
    is_external_db = db is not None
    if not is_external_db:
        db = SessionLocal()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        doc = db.query(Document).filter(Document.id == document_id).first()

        if not job or not doc:
            logger.error(f"Job {job_id} or Document {document_id} not found in DB.")
            return

        job.status = "running"
        job.progress = 85
        job.message = "Writing OKF concepts to disk..."
        db.commit()

        from app.services.okf_service import chunk_from_okf, write_okf_concepts

        okf_dir = os.path.join(settings.DATA_DIR, "knowledge", str(user_id), str(doc.topic_id))
        doc.okf_directory_path = okf_dir
        db.commit()

        write_okf_concepts(user_id, doc.topic_id, approved_concepts, okf_dir)

        job.progress = 90
        job.message = "Chunking semantic concepts..."
        db.commit()

        # Gather saved file paths by globbing the clustered directory structure.
        # write_okf_concepts() writes to concepts/cluster_<hub>/<slug>.md,
        # NOT the flat concepts/<slug>.md path, so we discover files on disk.
        from pathlib import Path as _Path
        concepts_dir = _Path(okf_dir) / "concepts"
        concept_files = [
            str(p) for p in concepts_dir.rglob("*.md")
            if p.name != "index.md"
        ]
        chunks_data = chunk_from_okf(concept_files)

        if not chunks_data:
            raise ValueError("OKF processing yielded zero text chunks.")

        job.progress = 95
        job.message = "Generating embeddings..."
        db.commit()

        texts = [text for _, text in chunks_data]
        embeddings = get_embeddings(texts)

        for idx, ((filepath, chunk_text_content), emb_vector) in enumerate(
            zip(chunks_data, embeddings)
        ):
            relative_path = os.path.relpath(filepath, okf_dir)
            chunk = ContentChunk(
                document_id=doc.id,
                user_id=user_id,
                topic_id=doc.topic_id,
                chunk_text=chunk_text_content,
                embedding=emb_vector,
                chunk_index=idx,
                okf_concept_path=relative_path,
            )
            db.add(chunk)

        doc.status = "parsed"
        job.status = "completed"
        job.progress = 100
        job.message = "Completed OKF structuring and vectorizing."
        db.commit()

        # Cleanup staging file
        staging_path = os.path.join(settings.DATA_DIR, "staging", f"{job_id}.json")
        if os.path.exists(staging_path):
            os.remove(staging_path)

    except Exception as e:
        db.rollback()
        logger.exception(f"Exception encountered during finalization (job {job_id}): {e}")
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


def update_concept_embeddings_task(
    document_id: uuid.UUID,
    topic_id: uuid.UUID,
    user_id: uuid.UUID,
    okf_dir: str,
    slugs: list[str],
    db: SessionLocal = None,
):
    """
    Background worker task to re-vectorize multiple OKF concepts after they have been expanded or modified.
    Drops old chunks for these specific concept files and generates new ones.
    """
    is_external_db = db is not None
    if not is_external_db:
        db = SessionLocal()

    try:
        from pathlib import Path

        from app.services.okf_service import chunk_from_okf

        base_dir = Path(okf_dir)
        concept_file_paths = []
        okf_concept_paths = []

        for slug in slugs:
            matches = list(base_dir.glob(f"concepts/*/{slug}.md"))
            if not matches:
                matches = list(base_dir.glob(f"concepts/{slug}.md"))
            if matches:
                concept_file_paths.append(str(matches[0]))
                cluster_name = matches[0].parent.name
                if cluster_name == "concepts":
                    okf_concept_paths.append(f"concepts/{slug}.md")
                else:
                    okf_concept_paths.append(f"concepts/{cluster_name}/{slug}.md")

        # Drop existing chunks for these files
        db.query(ContentChunk).filter(
            ContentChunk.document_id == document_id,
            ContentChunk.okf_concept_path.in_(okf_concept_paths),
        ).delete(synchronize_session=False)
        db.commit()

        # Re-chunk the modified files
        chunks_data = chunk_from_okf(concept_file_paths)

        if not chunks_data:
            logger.warning(f"No text chunks found for expanded concepts {slugs}")
            return

        texts = [text for _, text in chunks_data]
        embeddings = get_embeddings(texts)

        # Insert new chunks
        new_chunks = []
        for i, (path_str, text) in enumerate(chunks_data):
            # path is the absolute path, we need relative "concepts/cluster/slug.md"
            rel_path = Path(path_str).relative_to(base_dir).as_posix()
            new_chunks.append(
                ContentChunk(
                    document_id=document_id,
                    user_id=user_id,
                    topic_id=topic_id,
                    chunk_text=text,
                    embedding=embeddings[i] if embeddings else None,
                    chunk_index=i,
                    okf_concept_path=rel_path,
                )
            )

        db.bulk_save_objects(new_chunks)
        db.commit()
        logger.info(f"Successfully re-embedded {len(new_chunks)} chunks for {slugs}")

    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to update embeddings for concepts {slugs}: {e}")
    finally:
        if not is_external_db:
            db.close()
