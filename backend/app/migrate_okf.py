import sys

from sqlalchemy import text

from app.core.database import engine


def migrate() -> None:
    """
    Adds OKF columns to existing tables.
    """
    print("Running OKF DB Migration...")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE content_chunks ADD COLUMN IF NOT EXISTS okf_concept_path VARCHAR;"
                )
            )
            conn.execute(
                text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS okf_directory_path VARCHAR;")
            )
        print("Migration successful.")
    except Exception as e:
        print(f"Error during migration: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    migrate()
