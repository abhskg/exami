# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **OKF Ingestion Pipeline Integration**: Restructured the ingestion pipeline to support the Open Knowledge Format (OKF) standard. Ingested data is parsed into dynamic hierarchical concepts and parent-child links rather than flat summaries, and saved under a standardized structure (`index.md`, `log.md`, and clusters under `concepts/`) in the `./data/knowledge/{user_id}/{topic_id}/` workspace folder.
- **Interactive D3 Knowledge Graph**: Implemented an interactive D3.js-based force-directed Knowledge Graph visualization (`KnowledgeGraph.tsx`) in the frontend, complete with drag/drop, zoom/pan controls, dynamic link safety checks, and interactive node selection.
- **Staged Concept Review Workflow**: Added a staged concept review interface (`ReviewPanel.tsx` in the frontend) allowing users to approve, reject, or edit generated OKF concepts before finalizing the data load and performing text vectorization.
- **Dynamic Concept Expansion ("Go Deeper")**: Integrated a "Go Deeper" concept enrichment service (`expand_okf_concept` in backend and `ConceptDetailPanel.tsx` in frontend) enabling users to expand existing concept nodes with detailed LLM queries and automatically trigger background re-vectorization tasks (`update_concept_embeddings_task`).
- **Ingestion Reparse & Retry Support**: Implemented a retry and reparse endpoint (`POST /api/documents/{document_id}/reparse`) for failed document ingestion and web scans. Persists raw query and syllabus input parameters as metadata configuration on disk to allow exact web search retries, and exposed a retry action button (🔄) next to failed items in the Knowledge Catalog.
- **Increased System Limits & Optimized Prompts**:
  - Expanded maximum allowed character length for input syllabus and topic parameters from 1,000 to **100k characters** in API schemas and test suites.
  - Increased query source context slice limits and web scraping character caps from 10k to **30k characters** for more detailed retrieval.
  - Optimized LLM generation instructions to require extensive, fully elaborated OKF concept bodies.
- **MCQ Option Randomization**: Implemented option shuffling in `generate_questions()` using Python's `random.shuffle` before saving options. Shuffled options are mapped to `option_order` sequentially, guaranteeing correct option randomization.
- **SQLAlchemy Options Ordering**: Configured `Question.options` relationship in `backend/app/models/question.py` with `order_by="QuestionOption.option_order"` to automatically fetch options sorted by `option_order` across all backend API models and serializations.
- **Question Bank Analytics Dashboard**: Integrated a comprehensive, highly aesthetic analytics panel at the top of the Questions Bank view.
  - Left Column: Topic-specific stats showing Easy, Medium, and Hard question counts, a horizontal segmented/stacked progress bar showing the difficulty distribution, and a concept/tag frequency breakdown.
  - Right Column: Global subject/topic breakdown showing the total question counts across all of the user's topics, highlighting the currently active topic.
  - `backend/app/schemas/question.py` — added `TagAnalytics`, `TopicAnalytics`, and `QuestionAnalyticsResponse` schemas.
  - `backend/app/api/questions.py` — added `GET /api/questions/analytics` endpoint supporting topic-specific and user-wide global analytics.
  - `frontend/src/components/KnowledgeCatalog.tsx` — added types, state variables, and `fetchAnalytics` method to fetch analytics from the backend on load and when questions are created, updated, or deleted, and rendered the dashboard widgets before the filter section.
  - `backend/app/tests/test_question_bank.py` — added integration tests verifying the `/analytics` endpoint functionality for both topic-filtered and global requests.

- **Topic Rename & Delete from Sidebar**: Users can now edit and delete topics directly from the sidebar without leaving any page. Each topic row reveals a **✏️ pencil** (rename) and **🗑️ trash** (delete) icon button on hover. Clicking the pencil switches the row into an **inline rename editor** (Enter to save, Escape to cancel, duplicate-name guard included). Clicking the trash opens a **glassmorphic confirmation modal** that warns the user all associated data (documents, embeddings, questions, sessions, tags) will be permanently removed before proceeding.
  - `backend/app/schemas/topic.py` — added `TopicUpdate` schema with optional `name` and `description` fields.
  - `backend/app/api/topics.py` — added `PUT /api/topics/{id}` (rename with uniqueness check) and `DELETE /api/topics/{id}` (full cascade delete via SQLAlchemy `delete-orphan`).
  - `frontend/src/App.tsx` — imported `Pencil`, `Trash2`, `Check` from `lucide-react`; added `editingTopicId`, `editingTopicName`, `isRenamingTopic`, `confirmDeleteTopic`, `isDeletingTopic` state; added `handleRenameTopic()` and `handleDeleteTopic()` API handler functions; replaced plain topic row `<div>` with hover-aware rows supporting inline edit mode and action buttons.
  - `frontend/src/index.css` — added `.topic-row` / `.topic-actions` CSS rules to hide action buttons by default and reveal them with a smooth opacity transition on hover; the delete icon turns red on hover.

- **Elaborate Practice Mode Explanations**: Enhanced the MCQ generation LLM prompt (`backend/app/services/question_bank.py`) to produce comprehensive, multi-sentence explanations (minimum 4–6 sentences per question). Each explanation now covers: (1) why the correct answer is right with material references, (2) why each distractor is wrong addressing common misconceptions, (3) a real-world example or analogy for deeper understanding, and (4) any relevant formula, definition, or rule. The practice mode explanation panel in `frontend/src/App.tsx` was redesigned as a rich card with a colour-coded header (teal for correct, red for incorrect), a ✓/✗ badge, and explanation text split into sentence-level paragraphs with left-border accents for visual hierarchy.
- **Configurable Ingestion File Size Limit**: Extracted the hardcoded 15MB file size limit to environment variables (`MAX_FILE_SIZE_MB` in backend and `VITE_MAX_FILE_SIZE_MB` in frontend). The frontend dynamically syncs this value from the backend's `/health` endpoint while defaulting to the environment configuration.
- **Customizable Question Generation Count**: Introduced a dynamic question generation count selector (slider widget) in the frontend. Users can now choose to generate anywhere between 1 and 30 questions at once, replacing the previous hardcoded limit of 10.
- **Knowledge Catalog Dashboard**: Integrated a new sidebar tab and [KnowledgeCatalog.tsx](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/frontend/src/components/KnowledgeCatalog.tsx) client sub-view for comprehensive catalog administration (Documents, Embeddings/Chunks, Questions, and Tags).

### Fixed
- **Dangling Graph Links and Edge Sanitization**: Resolved D3 force simulation layout crashes by filtering out invalid or dangling parent-child edges in the frontend, and added backend sanitization of relationships in `load_okf_index` (supported by comprehensive unit tests).
- **Staging and OKF Directory Purges**: Consolidated filesystem cleanups by introducing a `_clear_dir` helper in `purge.py` to ensure all staging and OKF-specific directory trees are fully deleted when topics or documents are deleted.
- **Pathing and Recursive Globbing**: Resolved pathing issues under clustered subdirectories by replacing static file fetches with recursive `rglob` checks in `finalize_web_search_task` and concept endpoints.
- **Question Generation Failures (>10 Qs)**: Sliced question generation requests into batches of at most 5 questions in `backend/app/services/question_bank.py` to prevent API rate limits, response token exhaustion, timeouts, and JSON decode failures. Implemented resilient try-except block parsing per-question to avoid single-question failures from crashing the entire generation request.
- **Practice Mode Test Alignment**: Updated practice mode session assertion in `backend/app/tests/test_exams.py` to align with the recently introduced practice mode explanation feature, resolving a test suite failure.
- **Dropdown Option Menu Theming**: Fixed the dropdown select element glitch where options had white font on white background in Chromium browsers. Added `color-scheme: dark;` to `:root` and explicit styling on `select option` to use `var(--bg-secondary)` as the background and `var(--text-primary)` as the text color.
- **TypeScript Compiler Errors**: Resolved TypeScript compile errors:
  - Fixed implicit `any` parameter warning in the immediate explanation sentence mapping on `App.tsx` (line 3395) by adding explicit types `(sentence: string, idx: number)`.
  - Fixed unused state variable warning for `isLoadingAnalytics` in `KnowledgeCatalog.tsx` (line 131) by leveraging it to set a `0.6` opacity loading overlay with a smooth CSS transition over the analytics dashboard.
- **Empty Practice Mode Explanations**: Fixed an issue where explanations were not showing up after answering questions in practice mode. The backend API (`backend/app/api/exams.py`) was omitting the explanation payload during initial session creation because no questions were answered yet, and the submission endpoint didn't return the explanation. The backend now embeds the explanations upfront for practice mode sessions since the frontend already gracefully hides them until an option is selected.
- **React `key` Prop Warning in Explanation Panel**: Replaced bare array-index `key={idx}` with a content-based key (`\`${idx}-${sentence.slice(0, 30)}\``) in the practice-mode explanation sentence map, resolving the ESLint/React index-as-key warning.
- **Outdated Gemini Model Config**: Updated default LLM model from the deprecated `gemini-2.0-flash` to the currently active, cost-efficient, and supported `gemini-3.1-flash-lite` to resolve 404 NOT_FOUND API errors during MCQ question generation.
- **Gemini Embedding Generation**: Resolved a 404 NOT_FOUND error during text embedding generation by changing the default embedding model from `text-embedding-004` to `gemini-embedding-001`. Configured the API call to pass `output_dimensionality` corresponding to settings `EMBEDDING_DIMENSION` (768).




- **Document & Chunk CRUD APIs**: Implemented `PUT /api/documents/{id}` (rename), `DELETE /api/documents/{id}` (file and database cascade deletion), `GET /api/documents/{id}/chunks`, `PUT /api/documents/chunks/{id}` (updates chunk text and regenerates embedding vector), and `DELETE /api/documents/chunks/{id}`.
- **Question & Tag CRUD APIs**: Implemented `PUT /api/questions/{id}` (full MCQ editor including options and tags), `DELETE /api/questions/{id}`, `PUT /api/questions/tags/{id}` (renames tag with duplicate merging support), and `DELETE /api/questions/tags/{id}`.
- **Bulk Purge Utilities**: Created a transaction-safe database cleaning script [purge.py](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/backend/app/purge.py) and exposed `make purge-documents`, `make purge-questions`, `make purge-tags`, `make purge-topics`, and `make purge-all` targets in the root [Makefile](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/Makefile).
- **CRUD Integration Tests**: Added a new test suite [test_management.py](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/backend/app/tests/test_management.py) verifying all document, chunk, question, and tag CRUD features.
- **Centralized Logging Setup**: Added a centralized, structured logging setup using `logging.config.dictConfig` in `backend/app/core/logging_config.py`. Standardized console formats and silenced verbose logs from external packages (`sqlalchemy.engine`, `uvicorn.access`, etc.).
- **LOG_LEVEL Configuration**: Added a new configuration parameter `LOG_LEVEL` (default: "INFO") in settings (`app/core/config.py` and `.env` / `.env.example`).
- **HTTP Request Logging Middleware**: Implemented an ASGI middleware in `app/main.py` that intercepts all incoming requests to log method, path, query arguments, client host, duration, and status code.
- **Global Unhandled Exception Handler**: Embedded robust error handling in the middleware to catch all unhandled exceptions, log the stack trace using `logger.exception`, and return a clean 500 JSONResponse (`{"detail": "An unexpected error occurred. Please try again later."}`).
- **Client Error Exception Tracking**: Registered exception handlers on FastAPI for `HTTPException` and `RequestValidationError` to track client-side failures at warning log levels.
- **Endpoint Trace Instrumenting**: Instrumented API endpoints across `auth.py`, `topics.py`, `documents.py`, `exams.py`, and `questions.py` with structured info-level and warning-level log statements.
- **Logging Integration Tests**: Added test cases in `backend/app/tests/test_logging_exception.py` verifying request intercepting, unhandled exception catching, and HTTP validation/exception warnings.
- **Raw Text Ingestion Endpoint**: Added `POST /api/documents/raw-text` to ingest raw pasted text directly, save it to a `.txt` file, and process it in the background using the existing chunking/embedding pipeline.
- **Web Search Parser Ingestion Endpoint**: Added `POST /api/documents/web-search` to simulate parser agents by generating a mock parsed text corpus from syllabus requirements and target search topics.
- **Ingestion Integration Tests**: Added backend tests for both raw text paste and web search scraping in `backend/app/tests/test_ingestion.py`.
- **Frontend 3-Column Ingestion Wizard**: Replaced the static ingestion selector layout with a responsive 3-column glassmorphic method selector (File Upload, Raw Text, Web Search) in `frontend/src/App.tsx`.
- **Conditional Ingestion Forms**: Built modular form inputs for Raw Text (Title, Content) and Web Search (Title, Syllabus, Topics) with validation states and background task progress integrations.
- **Dynamic Provider Settings**: Updated the frontend to dynamically query the active LLM and embedding providers (`llm_provider`, `embedding_provider`) from the backend `/health` endpoint and reflect them in UI text logs and alerts.
- **Vector Similarity Query Function (Task 5.1)**: Implemented `get_similar_chunks()` in `backend/app/services/question_bank.py` using pgvector cosine distance (`<=>` operator) to retrieve the top-k semantically similar `ContentChunk` rows filtered strictly by `user_id` and `topic_id`. Supports a zeroed mock vector fallback in test/no-key environments.
- **Structured MCQ Generation Service (Task 5.2)**: Implemented `generate_questions()` which assembles chunk context, formulates a Gemini structured-output JSON prompt (`response_mime_type="application/json"`), parses returned `{question_text, options, explanation, tags, difficulty}` objects, and persists `Question`, `QuestionOption`, and `Tag` rows in a single DB transaction. Added `_resolve_or_create_tag()` to upsert tags respecting the `uq_tag_user_topic_name` unique constraint. Added `list_topic_tags()` helper for UI chip population.
- **Question Bank API (Task 5.2)**: Created `backend/app/api/questions.py` with three endpoints: `POST /api/questions/generate` (triggers generation), `GET /api/questions/` (lists saved questions with optional difficulty/tag filters), and `GET /api/questions/tags` (returns all topic tags). Registered the router in `api.py` and exported new schemas from `schemas/__init__.py`.
- **Question Pydantic Schemas (Task 5.2)**: Created `backend/app/schemas/question.py` defining `GenerateQuestionsRequest`, `GenerateQuestionsResponse`, `QuestionResponse`, `QuestionOptionResponse`, and `TagResponse`.
- **Exam Generator Config UI (Task 5.3)**: Replaced the placeholder Exam Simulator tab in `frontend/src/App.tsx` with a fully functional `ExamConfigPanel` featuring: topic selector, question count range slider (1–50), difficulty toggle (Easy/Medium/Hard/Mixed), tag filter chips (populated from DB tags + free-text entry with Enter-key support), animated Generate button calling `POST /api/questions/generate`, and an expandable MCQ preview list showing options (correct answer highlighted in teal), explanations, and tag badges.
- **Question Bank Tests (Task 5.1 & 5.2)**: Created `backend/app/tests/test_question_bank.py` with 13 tests covering: `get_similar_chunks()` isolation/limit/error behaviour, `generate_questions()` DB row counts and tag deduplication, and all three API endpoints (auth, 404, schema validation).
- **Exam Session Initializer API (Task 6.1)**: Developed `POST /api/exams/sessions` creating exam session scopes from database questions matching mode, tag filters, count, and difficulty configuration parameters, saving a frozen ordered list to `QuestionSet`.
- **Answer Submission & Time Verification Engine (Task 6.2)**: Developed `POST /api/exams/sessions/{id}/submit-answer` to record responses. Enforces server-side countdown limits and locks further edits if time limit is exceeded. Developed `POST /api/exams/sessions/{id}/complete` to explicitly close sessions, compute scores, and compile results.
- **Simulated Exam Interface & Results UI (Task 6.3)**: Created interactive simulation wrappers in React `App.tsx` containing client-side timers, navigation grids, selected option indicators, immediate explanation blocks for practice runs, circular scorecard heatmaps, and attempt review sheets.
- **Exam Engine Tests (Task 6.1 & 6.2)**: Created `backend/app/tests/test_exams.py` verifying transactional locks, timed expired rejections, response submissions, and automatic results calculations.

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
