import argparse
import os
import shutil
import sys
from pathlib import Path

# Add the parent directory to Python path to import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import engine
from app.models.content_chunk import ContentChunk
from app.models.document import Document
from app.models.question import Question, QuestionOption, question_tags
from app.models.tag import Tag
from app.models.topic import Topic


def purge_documents(db):
    print("Purging documents and content chunks...")
    db.query(Document).delete()
    db.query(ContentChunk).delete()
    db.commit()

    # Clear uploads directory on disk
    uploads_dir = Path(settings.UPLOADS_DIR)
    if uploads_dir.exists():
        print(f"Clearing storage uploads directory: {uploads_dir}")
        for path in uploads_dir.iterdir():
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
            except Exception as e:
                print(f"Failed to delete {path}: {e}")
    print("Documents and content chunks purged successfully.")


def purge_questions(db):
    print("Purging questions, options, and associations...")
    db.query(QuestionOption).delete()
    db.query(Question).delete()
    db.execute(question_tags.delete())
    db.commit()
    print("Questions and options purged successfully.")


def purge_tags(db):
    print("Purging all taxonomy tags...")
    db.execute(question_tags.delete())
    db.query(Tag).delete()
    db.commit()
    print("Tags purged successfully.")


def purge_topics(db):
    print("Purging all study topics (cascades to linked documents, questions, tags, and exams)...")
    db.query(Topic).delete()
    db.commit()

    # Also clean up disk files since documents are deleted
    uploads_dir = Path(settings.UPLOADS_DIR)
    if uploads_dir.exists():
        print(f"Clearing storage uploads directory: {uploads_dir}")
        for path in uploads_dir.iterdir():
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
            except Exception as e:
                print(f"Failed to delete {path}: {e}")
    print("Topics and all cascaded data purged successfully.")


def main():
    parser = argparse.ArgumentParser(description="Purge AI Exam Portal data.")
    parser.add_argument(
        "--documents",
        action="store_true",
        help="Purge all documents, content chunks, and files on disk.",
    )
    parser.add_argument("--questions", action="store_true", help="Purge all questions and options.")
    parser.add_argument("--tags", action="store_true", help="Purge all taxonomy tags.")
    parser.add_argument(
        "--topics",
        action="store_true",
        help="Purge all topics (cascades to all other data) and disk files.",
    )
    parser.add_argument("--all", action="store_true", help="Purge everything.")

    args = parser.parse_args()

    if not (args.documents or args.questions or args.tags or args.topics or args.all):
        parser.print_help()
        sys.exit(1)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        if args.all:
            print("Purging ALL data from database and disk...")
            purge_topics(db)
            purge_questions(db)
            purge_tags(db)
            purge_documents(db)
        else:
            if args.topics:
                purge_topics(db)
            if args.documents:
                purge_documents(db)
            if args.questions:
                purge_questions(db)
            if args.tags:
                purge_tags(db)

        print("Purge operation completed successfully.")
    except Exception as e:
        print(f"Error during purge: {e}", file=sys.stderr)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
