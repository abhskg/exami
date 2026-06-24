# Development Roadmap & Implementation Tasks

## ExamI — Local-First MVP

This document maintains the step-by-step roadmap for implementing the Local-First MVP. It defines the specific action items, goals, and dependencies for each phase of the build sequence.

---

## 🗂️ Roadmap Index

1. [Phase 1: Core Configuration & Database Plumbing](#phase-1-core-configuration--database-plumbing)
2. [Phase 2: Auth, User Management & isolation context](#phase-2-auth-user-management--isolation-context)
3. [Phase 3: Database Models & Schema Migration](#phase-3-database-models--schema-migration)
4. [Phase 4: Document Ingestion & Background Processing](#phase-4-document-ingestion--background-processing)
5. [Phase 5: Question Bank & Gemini MCQ Generation](#phase-5-question-bank--gemini-mcq-generation)
6. [Phase 6: Exam Engine & Simulation Loop](#phase-6-exam-engine--simulation-loop)
7. [Phase 7: Review Analytics & UI Visualizations](#phase-7-review-analytics--ui-visualizations)

---

## Phase 1: Core Configuration & Database Plumbing

**Goal:** Establish a working backend settings system and verify connection pool access to the Postgres instance.

### Task 1.1: Build Application Environment Settings Loader

- [x] **Action Steps:**
  - Create `backend/app/core/config.py`.
  - Use `pydantic-settings` to define a `Settings` class that parses env variables.
  - Load database URL, secret keys, file directory path, and Gemini API keys.
- [x] **Target Goal:** Settings load successfully from `.env` and fail gracefully with informative validation errors if keys are missing.
- [x] **Dependencies:** None.

### Task 1.2: Initialize SQLAlchemy Connection Pool

- [x] **Action Steps:**
  - Create `backend/app/core/database.py`.
  - Initialize the SQLAlchemy engine (using `psycopg2` driver).
  - Configure connection pool parameters suited for local VPS limits (e.g., `pool_size=10`, `max_overflow=20`).
  - Create a session maker (`SessionLocal`) and a DB session yield function `get_db()`.
- [x] **Target Goal:** Successful connection validation through CLI check.
- [x] **Dependencies:**
  - Database service started: `docker compose up -d` ([docker-compose.yml](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/docker-compose.yml)).
  - [Task 1.1](#task-11-build-application-environment-settings-loader) completed.

---

## Phase 2: Auth, User Management & Isolation Context

**Goal:** Establish user workspaces. All API routes require extraction of `user_id` to enforce row-level security.

### Task 2.1: Implement Security & Hashing Utilities

- [x] **Action Steps:**
  - Create `backend/app/core/security.py`.
  - Implement password hashing and verification using `passlib` with `bcrypt`.
  - Implement JWT token generation and validation using `python-jose`.
- [x] **Target Goal:** Create and parse JSON Web Tokens securely.
- [x] **Dependencies:** None.

### Task 2.2: Implement Auth Routers & User Models

- [x] **Action Steps:**
  - Create database model `User` under `backend/app/models/user.py`.
  - Create `/api/auth/register` (hashing password and saving user).
  - Create `/api/auth/login` (verifying credentials and returning JWT token).
- [x] **Target Goal:** User record created and JWT token successfully returned on correct login request.
- [x] **Dependencies:** [Task 1.2](#task-12-initialize-sqlalchemy-connection-pool) (DB pool availability) & [Task 2.1](#task-21-implement-security--hashing-utilities).

### Task 2.3: Create FastAPI Current User Dependency

- [x] **Action Steps:**
  - Create `backend/app/api/deps.py`.
  - Add a dependency injection function `get_current_user` that extracts the token, decodes the username/id, and queries the database.
- [x] **Target Goal:** Secure any route by adding `current_user: User = Depends(get_current_user)` as a parameter.
- [x] **Dependencies:** [Task 2.2](#task-22-implement-auth-routers--user-models).

### Task 2.4: Create Authentication UI

- [x] **Action Steps:**
  - Build React components `LoginForm.tsx` and `SignupForm.tsx` in the frontend page folders.
  - Connect them to local storage (saving JWT token) and navigate to the dashboard.
- [x] **Target Goal:** Logged-in state persists in React storage, showing user profile.
- [x] **Dependencies:** [Task 2.2](#task-22-implement-auth-routers--user-models) (Backend login endpoints ready).

---

## Phase 3: Database Models & Schema Migration

**Goal:** Map the relational tables described in the database design document to SQLAlchemy ORM configurations.

### Task 3.1: Define Relational Schemas

- [x] **Action Steps:**
  - Create models in `backend/app/models/` for:
    - `Topic`: Scopes datasets and tags.
    - `Document`: Metadata for uploads.
    - `ContentChunk`: Stores chunk texts and the `pgvector` embedding vector.
    - `Tag`: Supports conceptual hierarchical associations.
    - `Question` & `QuestionOption`: Question bank details.
    - `QuestionSet`: Saved practice configurations.
    - `ExamSession` & `ExamResponse`: Simulated score logging.
- [x] **Target Goal:** Models match [03-data-schema-design.md](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/03-data-schema-design.md) mappings.
- [x] **Dependencies:** [Task 1.2](#task-12-initialize-sqlalchemy-connection-pool) completed.

### Task 3.2: Database Initialization Script

- [x] **Action Steps:**
  - Create database init command logic.
  - Ensure the database executes `CREATE EXTENSION IF NOT EXISTS vector` prior to creating tables.
  - Automatically map SQLAlchemy metadata (`Base.metadata.create_all`).
- [x] **Target Goal:** Running the init script establishes a clean, ready schema in PostgreSQL.
- [x] **Dependencies:** [Task 3.1](#task-31-define-relational-schemas).

---

## Phase 4: Document Ingestion & Background Processing

**Goal:** Process uploaded PDF/text files into vector chunks using background workers.

### Task 4.1: Implement File Storage & Upload APIs

- [x] **Action Steps:**
  - Build a route `/api/documents/upload` accepting files.
  - Save file to directory: `./data/uploads/{user_id}/{document_id}.pdf`.
  - Validate file size limit (15MB) and type.
  - Insert record in `documents` with status `pending`.
- [x] **Target Goal:** Uploaded files write to local folder successfully and create database metadata.
- [x] **Dependencies:** [Task 2.3](#task-23-create-fastapi-current-user-dependency) (for user isolation context) & [Task 3.2](#task-32-database-initialization-script).

### Task 4.2: Build Background Worker & Job State Engine

- [x] **Action Steps:**
  - Create a simple jobs schema in DB (`jobs` table with `status`, `task_type`, `progress`).
  - Wire up a FastAPI background task handler.
  - Create `/api/jobs/{job_id}` status endpoints.
- [x] **Target Goal:** API triggers async processing and responds immediately while the job runs in background.
- [x] **Dependencies:** [Task 3.2](#task-32-database-initialization-script).

### Task 4.3: Implement Parser & Embedder Pipeline (Gemini Integration)

- [x] **Action Steps:**
  - Build PDF/text processing functions.
  - Integrate Gemini Embeddings API (via `google-genai` SDK) to vectorize extracted text chunks.
  - Write parsed chunks and vector values directly to the `content_chunks` table.
- [x] **Target Goal:** Extracted text is successfully chunked, vectorized, and stored in pgvector columns.
- [x] **Dependencies:** [Task 4.2](#task-42-build-background-worker-job-state-engine).

### Task 4.4: Ingestion UI Wizard

- [x] **Action Steps:**
  - Build the React file upload drop zone.
  - Wire up polling requests calling `/api/jobs/{job_id}` to show progress bars.
- [x] **Target Goal:** Visual representation of uploading, parsing, and successful chunk storage indicators.
- [x] **Dependencies:** [Task 4.1](#task-41-implement-file-storage--upload-apis) & [Task 4.2](#task-42-build-background-worker-job-state-engine).

---

## Phase 5: Question Bank & Gemini MCQ Generation

**Goal:** Implement similarity searches to compile relevant context and use Gemini to generate tagged MCQs.

### Task 5.1: Vector Similarity Query Function

- [x] **Action Steps:**
  - Write standard SQL query using pgvector's operators (e.g. `<->` Euclidean distance or `<~>` cosine distance).
  - Retrieve the top `k` chunks matching target query keywords or tags, filtered strictly by `user_id` and `topic_id`.
- [x] **Target Goal:** Return semantic context blocks associated with chosen terms.
- [x] **Dependencies:** [Task 4.3](#task-43-implement-parser--embedder-pipeline-gemini-integration).

### Task 5.2: Structured MCQ Generation Service (Gemini API)

- [x] **Action Steps:**
  - Formulate structured prompt targeting Gemini API.
  - Use Gemini's structured JSON output configuration (`response_mime_type="application/json"`) to return:
    - `question_text`, `options` (array of text and correctness boolean), `explanation` (why it's correct), and `tags` (suggested tags).
  - Save the questions, options, and tags inside a database transaction.
- [x] **Target Goal:** Successfully save high-quality MCQs mapped to parsed tags.
- [x] **Dependencies:** [Task 5.1](#task-51-vector-similarity-query-function).

### Task 5.3: Exam Generator Config UI

- [x] **Action Steps:**
  - Design the `ExamConfigPanel` React UI mapping: question counts, tags selection, difficulty toggles.
- [x] **Target Goal:** Configuration is successfully packed into a payload and sent to backend generator APIs.
- [x] **Dependencies:** [Task 5.2](#task-52-structured-mcq-generation-service-gemini-api).

---

## Phase 6: Exam Engine & Simulation Loop

**Goal:** Track practice sets and enforce timing constraints server-side during timed sessions.

### Task 6.1: Exam Session Initializer API

- [x] **Action Steps:**
  - Create endpoint `/api/exams/sessions` parameterizing mode (timed vs practice), tags, count, and difficulty.
  - Create `exam_sessions` record and fetch matching questions.
- [x] **Target Goal:** Create exam workspace state returned in a clean API payload.
- [x] **Dependencies:** [Task 5.2](#task-52-structured-mcq-generation-service-gemini-api).

### Task 6.2: Answer Submission & Time Verification Engine

- [x] **Action Steps:**
  - Implement `/api/exams/sessions/{id}/submit-answer` logging selections to `exam_responses`.
  - Validate timed rules: if current time exceeds `started_at` + `time_limit_seconds`, auto-lock changes and reject request.
- [x] **Target Goal:** Answer logging operates seamlessly; prevents tampering with time constraints.
- [x] **Dependencies:** [Task 6.1](#task-61-exam-session-initializer-api).

### Task 6.3: Simulated Exam Interface UI

- [x] **Action Steps:**
  - Build React components: `QuestionCard`, `TimerBar` (updates remaining time, automatically locks on 0), and `NavigationShell`.
- [x] **Target Goal:** Responsive layout for navigating between questions and answering.
- [x] **Dependencies:** [Task 6.2](#task-62-answer-submission--time-verification-engine).

---

## Phase 7: Review Analytics & UI Visualizations

**Goal:** Aggregate correct/incorrect answers into visually intuitive tag-based heatmaps.

### Task 7.1: Score Aggregator API

- [ ] **Action Steps:**
  - Implement endpoint `/api/exams/sessions/{id}/results`.
  - Query DB to compile overall score, speed, and percent correct per tag.
- [ ] **Target Goal:** Return dashboard payload mapping scores.
- [ ] **Dependencies:** [Task 6.2](#task-62-answer-submission--time-verification-engine).

### Task 7.2: Build Tag Heatmap Component

- [ ] **Action Steps:**
  - Render concept maps styling tags dynamically (e.g. green for strong, red for weak).
  - Add button "Practice Weak Areas" that initiates question generation specifically scoped to weak tags.
- [ ] **Target Goal:** Custom feedback visualizations mapping user capabilities.
- [ ] **Dependencies:** [Task 7.1](#task-71-score-aggregator-api) & [Task 5.2](#task-52-structured-mcq-generation-service-gemini-api) (for targeted generation triggering).
