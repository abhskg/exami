import sys
from sqlalchemy import text
from app.core.database import Base, engine
# Import all models to ensure they are registered on the Base metadata
from app.models.user import User
from app.models.topic import Topic
from app.models.document import Document
from app.models.content_chunk import ContentChunk
from app.models.tag import Tag
from app.models.question import Question, QuestionOption, question_tags
from app.models.question_set import QuestionSet, QuestionSetItem
from app.models.exam import ExamSession, ExamResponse

def init_db() -> None:
    """
    Initializes the database schema.
    1. Ensures pgvector extension is enabled.
    2. Generates all schema tables.
    """
    print("Connecting to database and creating vector extension if not exists...")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        print("Vector extension checked/created successfully.")
    except Exception as e:
        print(f"Error creating vector extension: {e}", file=sys.stderr)
        print("Make sure pgvector is installed and the database user has superuser privileges.", file=sys.stderr)
        sys.exit(1)

    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("All database tables created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    init_db()
