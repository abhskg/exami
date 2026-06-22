# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Vector Similarity Query Function (Task 5.1)**: Implemented `get_similar_chunks()` in `backend/app/services/question_bank.py` using pgvector cosine distance (`<=>` operator) to retrieve the top-k semantically similar `ContentChunk` rows filtered strictly by `user_id` and `topic_id`. Supports a zeroed mock vector fallback in test/no-key environments.
- **Structured MCQ Generation Service (Task 5.2)**: Implemented `generate_questions()` which assembles chunk context, formulates a Gemini structured-output JSON prompt (`response_mime_type="application/json"`), parses returned `{question_text, options, explanation, tags, difficulty}` objects, and persists `Question`, `QuestionOption`, and `Tag` rows in a single DB transaction. Added `_resolve_or_create_tag()` to upsert tags respecting the `uq_tag_user_topic_name` unique constraint. Added `list_topic_tags()` helper for UI chip population.
- **Question Bank API (Task 5.2)**: Created `backend/app/api/questions.py` with three endpoints: `POST /api/questions/generate` (triggers generation), `GET /api/questions/` (lists saved questions with optional difficulty/tag filters), and `GET /api/questions/tags` (returns all topic tags). Registered the router in `api.py` and exported new schemas from `schemas/__init__.py`.
- **Question Pydantic Schemas (Task 5.2)**: Created `backend/app/schemas/question.py` defining `GenerateQuestionsRequest`, `GenerateQuestionsResponse`, `QuestionResponse`, `QuestionOptionResponse`, and `TagResponse`.
- **Exam Generator Config UI (Task 5.3)**: Replaced the placeholder Exam Simulator tab in `frontend/src/App.tsx` with a fully functional `ExamConfigPanel` featuring: topic selector, question count range slider (1–50), difficulty toggle (Easy/Medium/Hard/Mixed), tag filter chips (populated from DB tags + free-text entry with Enter-key support), animated Generate button calling `POST /api/questions/generate`, and an expandable MCQ preview list showing options (correct answer highlighted in teal), explanations, and tag badges.
- **Question Bank Tests (Task 5.1 & 5.2)**: Created `backend/app/tests/test_question_bank.py` with 13 tests covering: `get_similar_chunks()` isolation/limit/error behaviour, `generate_questions()` DB row counts and tag deduplication, and all three API endpoints (auth, 404, schema validation).

- **Database Models & Relationships (Task 3.1)**: Created SQLAlchemy ORM models mapping `Topic`, `Document`, `ContentChunk`, `Tag`, `Question`, `QuestionOption`, `QuestionSet`, `QuestionSetItem`, `ExamSession`, and `ExamResponse`. Made embedding vector sizes configurable via `EMBEDDING_DIMENSION` defaulting to 768 (Gemini standard).
- **Schema Initialization Script (Task 3.2)**: Added a database initializer command (`python -m app.init_db`) that runs `CREATE EXTENSION IF NOT EXISTS vector` before mapping ORM metadata. Wired it into FastAPI lifespan hooks and unit test database fixture configurations.
- **Database Port Mapping & Configuration**: Changed PostgreSQL default port mapping in `docker-compose.yml` from 5432 to 5434 to prevent conflicts with native Windows services, and updated backend `.env` variables accordingly.
- **Model Integrity Tests**: Created transactional validation checks in `backend/app/tests/test_models.py` verifying relationships, unique constraints, and cascade delete rules.
- **Document Ingestion & Upload APIs (Task 4.1)**: Developed `POST /api/documents/upload` accepting PDF, TXT, and MD files under 15MB, saving files locally at `./data/uploads/{user_id}/{document_id}{suffix}`. Created `GET /api/documents/` to fetch topic-specific metadata.
- **Background Worker & Job State Engine (Task 4.2)**: Created `Job` model and schemas to track task status (`pending`, `running`, `completed`, `failed`), progress metrics (0-100%), and error logs. Implemented FastAPI background task runners and the `GET /api/jobs/{job_id}` status polling endpoint.
- **Parser & Embedder Pipeline (Task 4.3)**: Integrated the Google GenAI SDK to call the `text-embedding-004` model. Added text extraction from PDFs via `pypdf`, chunking at word boundaries with overlapping segments, and database loading via `pgvector`. Configured mock fallbacks for local/test environments lacking live keys.
- **Ingestion UI Wizard (Task 4.4)**: Integrated dynamic frontend state in React `App.tsx` including DB-backed topic dropdown selectors, topic creation forms, a drag-and-drop file upload zone, active job progress bars showing current pipeline steps, and dynamic document list status chips.
- **Ingestion Integration Tests (Task 4.5)**: Created `backend/app/tests/test_ingestion.py` covering size/extension rules, DB record assertions, synchronous task workers, and job polling endpoints.

## [0.1.1] - 2026-06-22

### Added
- **Settings Loader (Task 1.1)**: Added a configuration loader utilizing `pydantic-settings` to dynamically parse and validate environments from a `.env` file, and integrated it into `backend/app/main.py`.
- **Validation Tests**: Introduced configuration and validation tests under `backend/app/tests/test_config.py`.
- **SQLAlchemy Connection Pool (Task 1.2)**: Initialized SQLAlchemy connection pool engine with standard local settings (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`) in `backend/app/core/database.py` and implemented the FastAPI dependency generator `get_db()`.
- **Security & Hashing Utilities (Task 2.1)**: Built password hashing and verification utilities using `bcrypt` directly to ensure robust security, and python-jose wrappers for encoding/decoding JWT access tokens. Added unit tests under `backend/app/tests/test_security.py`.
- **Auth Routers & User Models (Task 2.2)**: Defined the relational `User` database model mapping to the `users` table, created Pydantic validation schemas (`UserCreate`, `UserResponse`, `UserLogin`, `Token`, `TokenData`), and implemented `/api/auth/register` and `/api/auth/login` endpoints. Added integration tests under `backend/app/tests/test_auth.py`.
- **FastAPI Current User Dependency (Task 2.3)**: Built the `get_current_user` dependency utilizing `OAuth2PasswordBearer` to extract and validate bearer tokens, decode client credentials, and resolve user contexts. Integrated a prototype endpoint `/api/users/me` and added dependency tests in `backend/app/tests/test_deps.py`.
- **Authentication UI (Task 2.4)**: Developed modular React components `LoginForm.tsx` and `SignupForm.tsx` integrating input validation, state transitions, and automatic login flow. Built the split-layout container `AuthPage.tsx` using the HSL color palette and glassmorphism styling, and integrated state persistence to manage session tokens and dynamic user details inside `App.tsx`. Configured frontend environment variables (`.env`, `.env.example`) to dynamically resolve `VITE_API_URL` endpoints, created type definitions (`src/vite-env.d.ts`) to enable TypeScript recognition of client-side imports, and updated the ingested documents list to initialize empty with a styled warning placeholder.

## [0.1.0] - 2026-06-22

### Added

#### 📂 Scaffolding & Directory Layouts
- **Backend structure**: Initialized python application package directory under `backend/app/` with module boundaries for:
  - `app/api/` (API endpoints/routing)
  - `app/core/` (Configurations, database connections, security)
  - `app/models/` (SQLAlchemy relational mapping classes)
  - `app/schemas/` (Pydantic schema definitions)
  - `app/services/` (Core logic: Ingestion, Question Bank, Exam Engine)
  - `app/workers/` (In-process task runners)
- **Frontend structure**: Set up a typescript React project directory layout under `frontend/src/` with sub-packages:
  - `src/components/` (Reusable shared UI widgets)
  - `src/pages/` (Login, Dashboard, Setup Wizard, Exam Simulator, Results View)
  - `src/hooks/` (Custom reactive logic scripts)
  - `src/services/` (HTTP/REST endpoints integration client)
- **Data storage structure**: Created local storage directory `data/uploads/` to maintain raw documents uploaded by users.

#### ⚙️ Configuration & Tooling Setup
- **Root-level Git ignore**: Created `.gitignore` excluding Python build outputs, virtual environments (`.venv`), Node dependency trees (`node_modules`), build directories (`dist/`), local environment keys (`.env*`), and the user uploads directory (`data/`).
- **Database Orchestration**: Added a root `docker-compose.yml` configured to pull `pgvector/pgvector:pg16` to simplify standing up a local Postgres instances with pgvector enabled.
- **Vite Bundler Config**: Configured `frontend/vite.config.ts` running the React plugin on dev server port `3000`.
- **TypeScript Config**: Configured `frontend/tsconfig.json` targeting ES2020 and mapping module resolution for React/Vite development.
- **Environment Template**: Created `backend/.env.example` mapping out database URLs, app environment states, JWT parameters, and API configuration requirements.

#### 📦 Project Dependency Manifests
- **Python Backend**: Created `backend/requirements.txt` containing dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2-binary`, `pgvector`, `pydantic`, `google-genai`, `python-dotenv`, `python-multipart`, `jose`, `passlib[bcrypt]`, `pytest`, `httpx`.
- **Node Frontend**: Created `frontend/package.json` mapping scripts (`dev`, `build`, `preview`) and core libraries: `react`, `react-dom`, `react-router-dom`, and `lucide-react`.

#### 💻 Main Entrypoints & UI Boilerplate
- **FastAPI Core**: Created `backend/app/main.py` with app metadata, CORS policies allowing cross-origin requests, and status health check endpoints (`/` and `/health`).
- **Premium Styling Foundations**: Created `frontend/src/index.css` defining custom slate, indigo, and violet HSL variables, smooth transitions, styling for buttons and forms, and layout settings using glassmorphism designs.
- **Interactive Prototyping**: Created `frontend/src/App.tsx` implementing a fully responsive interface shell featuring:
  - Sticky sidebar navigation toggles.
  - Interactive Database connection indicator (simulating PostgreSQL availability).
  - Multi-page simulated routes (Dashboard, Setup Wizard, Exam Simulator, Results).
  - Checklist tracking of workspace modules and files.
- **HTML Container**: Created `frontend/index.html` loading premium Google fonts (Outfit and Inter) and binding React's execution script.

