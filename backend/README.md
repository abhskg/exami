# 🐍 ExamI — Backend

This is the backend service for **ExamI**, built using **FastAPI** (Python 3.10+) and integrated with a **PostgreSQL** database featuring the **pgvector** extension. It handles user authentication, document parsing, semantic text chunking, vector embeddings, Gemini-powered question generation, and simulated exam session states.

---

## 🛠️ Key Technologies & Libraries

*   **FastAPI**: Modern, high-performance web framework for building APIs.
*   **SQLAlchemy (v2.0+)**: SQL toolkit and Object Relational Mapper (ORM).
*   **pgvector**: PostgreSQL vector similarity search extension.
*   **Google GenAI SDK**: For calling the Gemini models (`gemini-embedding-001` and `gemini-3.1-flash-lite`).
*   **Pydantic (v2.0+)**: Data validation and settings management using python type annotations.
*   **PyPDF**: PDF content extraction.
*   **Pytest**: Robust test suite execution.
*   **python-jose & bcrypt**: Security hashing and JSON Web Token (JWT) token utilities.

---

## 📁 Directory Structure

```
backend/
├── app/
│   ├── api/            # API endpoints & route logic
│   │   ├── auth.py       # User registration, login, and profile
│   │   ├── documents.py  # PDF/TXT uploads and document metadata queries
│   │   ├── exams.py      # Exam session creation, question sets, submissions
│   │   ├── jobs.py       # Ingestion task queue status checking
│   │   └── questions.py  # Vector similarity & structured Gemini MCQ generation
│   │
│   ├── core/           # Core configuration & DB connection engines
│   │   ├── config.py     # Pydantic Settings loader for environments
│   │   ├── database.py   # SQLAlchemy engine connection & SessionLocal dependency
│   │   └── security.py   # Token encryption, decryption, password hashing
│   │
│   ├── models/         # SQLAlchemy ORM Database Schemas
│   │   ├── content_chunk.py # Text blocks, tokens, and Vector Embeddings
│   │   ├── document.py      # Raw document file registers
│   │   ├── exam.py          # Exam attempts, session parameters, and answers
│   │   ├── question_set.py  # Frozen lists of questions assigned to sessions
│   │   ├── question.py      # MCQs, options, difficulty maps, and tag connections
│   │   ├── tag.py           # Subject tags with unique constraints
│   │   ├── topic.py         # Parent topic spaces
│   │   └── user.py          # Hashed user registers
│   │
│   ├── schemas/        # Pydantic Validation & Serialization Templates
│   │   ├── auth.py          # Register, login, and response structures
│   │   ├── document.py      # Document upload schemas
│   │   ├── exam.py          # Attempt details, submission shapes, results
│   │   ├── job.py           # Task states and tracking progress
│   │   ├── question.py      # Input queries and validated response models
│   │   ├── tag.py           # Tag names and IDs
│   │   └── topic.py         # Topic details and creations
│   │
│   ├── services/       # Business Logic Modules
│   │   ├── exam_engine.py      # Scoring calculations, timeout verifications
│   │   ├── ingestion.py        # PDF extraction, overlaps, and embeddings pipeline
│   │   └── question_bank.py    # Cosine similarity matching, Gemini structures
│   │
│   ├── workers/        # Asynchronous processing engine
│   │   └── ingestion_worker.py # In-process queue runners
│   │
│   ├── tests/          # pytest unit and integration tests
│   │   ├── conftest.py         # Pytest fixtures and mock client database configurations
│   │   ├── test_auth.py        # User authentication routers
│   │   ├── test_config.py      # Pydantic environment configurations
│   │   ├── test_exams.py       # Submission timeouts, scoring, locks
│   │   ├── test_ingestion.py   # Upload formats, jobs, embedding mock fallbacks
│   │   └── test_question_bank.py # Cosine queries, tag deduplications, endpoints
│   │
│   ├── init_db.py      # Schema initializer script
│   └── main.py         # Main entry point & CORS configuration
│
├── data/               # Local media & uploaded documents directory (ignored)
├── requirements.txt    # Python package dependencies
├── pyproject.toml      # Formatting/test metadata configs
└── .env.example        # Environment variable template
```

---

## ⚙️ Environment Configuration

Copy `backend/.env.example` to `backend/.env` and update the variables:

```ini
APP_NAME="ExamI"
APP_ENV=local
DEBUG=True

# Note: Using port 5434 to avoid conflicts with native PostgreSQL installs
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/ai_exam_portal

SECRET_KEY="super-secret-key-change-in-production"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Obtain this key from Google AI Studio (https://aistudio.google.com/)
GEMINI_API_KEY="your-gemini-api-key"

UPLOADS_DIR="./data/uploads"
```

---

## 🚀 Setup & Execution

### Prerequisites
*   Python 3.10 or higher.
*   Docker Desktop running (for database container).

### Running Locally
1.  **Start Database**:
    Ensure the postgres database container is up:
    ```bash
    docker compose up -d
    ```
2.  **Activate virtual environment**:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # Linux/Mac:
    source .venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Initialize Schema**:
    Enable the `pgvector` extension and compile SQLAlchemy schemas:
    ```bash
    python -m app.init_db
    ```
5.  **Start Dev Server**:
    Launch the FastAPI Uvicorn engine:
    ```bash
    uvicorn app.main:app --reload
    ```
    The server will run on `http://127.0.0.1:8000`. You can access interactive documentation at `http://127.0.0.1:8000/docs`.

---

## 🧪 Testing

The backend includes 30+ tests asserting database locks, query calculations, worker states, and mock embedding fallbacks (used when `GEMINI_API_KEY` is not present in tests).

To execute tests:
```bash
# Activate .venv first, then:
pytest -v
```

---

## 🛠️ Code Style Configuration

Code formatting and testing guidelines are managed via [pyproject.toml](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/backend/pyproject.toml). Pre-configured tools include:
*   **Black** for consistent formatting rules.
*   **iSort** for organized import declarations.
*   **Pytest** for unit assertions.
