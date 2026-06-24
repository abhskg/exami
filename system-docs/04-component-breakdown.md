# Component Breakdown
## ExamI — Local-First MVP

---

## 1. Purpose

This document provides a structural inventory of the UI components and backend modules required for the lean, local-first version of the portal. Compared to the original enterprise breakdown, the backend collapses from nine services into **four modules inside a single application**, and the AI layer collapses from five agents into **two**. Everything below maps onto the System Architecture and Data Schema documents.

---

## 2. Frontend Components

These are essentially unchanged from the original design — the simplification here is almost entirely on the backend/infra side, not the UI surface.

### 2.1 Auth & Account
- `LoginForm`
- `SignupForm`
- `AccountSettingsPanel` (kept minimal at this stage — no plan tiers or billing needed for a local-first deployment)

### 2.2 Setup / Input Module
- `SetupWizard` (top-level container, step-driven)
  - `ModeSelector` — "Practice existing set" vs. "Generate new from dataset" vs. "Start new topic"
  - `TopicPicker` — lists existing topics for the logged-in user
  - `QuestionSetPicker` — lists saved question sets under a chosen topic
  - `DatasetPicker` — lists ingested knowledge-base content under a chosen topic, for fresh generation
  - `SyllabusTextInput` — free-text topic/syllabus entry
  - `FileUploadInput` — PDF/document upload with progress indicator
  - `ExamConfigPanel` — question count, difficulty, mode (Practice/Timed), timer length, tag filters
  - `IngestionProgressIndicator` — simple polling (every few seconds) of a job-status endpoint; no WebSocket/SSE needed at this scale

> `WebScanToggle` (the optional web-research input) is dropped from the MVP scope — it can be reintroduced later without affecting anything else here.

### 2.3 Knowledge Base Browser
- `TopicTreeView` — hierarchical view of topics → sub-topics/tags
- `TagChipList` — selectable tag filters (multi-select)
- `DocumentList` — ingested source documents per topic, with status
- `QuestionSetList` — saved, reusable question sets per topic
- `DeepDiveConfirmationModal` — "We're adding this under your existing [Topic] — confirm?"

### 2.4 Exam Interface
- `ExamSessionContainer` (top-level, mode-aware)
  - `QuestionCard` — stem + options, single-select
  - `AnswerFeedbackPanel` — shown only in Practice Mode, immediate correct/incorrect + explanation
  - `TimerBar` — shown only in Timed Mode, server-synced countdown
  - `QuestionNavigator` — jump between questions, flag-for-review markers
  - `ExamSubmitConfirmModal`
  - `AutoSubmitHandler` (non-visual logic component) — triggers submission on time expiry

### 2.5 Results & Review
- `ResultsSummaryCard` — score, time taken, pass/fail if applicable
- `TagPerformanceHeatmap` — per-tag strength/weakness visualization
- `QuestionReviewList` — per-question breakdown: user answer vs. correct answer vs. explanation
- `GenerateMoreOnWeakTagButton` — triggers a scoped regeneration request from a weak tag
- `AttemptHistoryTable` — past attempts on the same set/topic over time

### 2.6 Shared / Cross-Cutting UI
- `NavigationShell` (header, sidebar, topic switcher)
- `ToastNotificationSystem` (job completion, errors)
- `LoadingSkeletons` (for async ingestion/generation waits)
- `ErrorBoundary` / `EmptyStateMessages` (e.g., "No question sets yet — generate your first one")

---

## 3. Backend Modules (Single Application, Not Separate Services)

All four modules below live in **one deployable backend application**, sharing one database connection and one process. They're still cleanly separated internally (own routes, own data-access code) so any one of them could be peeled out into its own service later — but for now there's nothing to deploy, scale, or monitor separately.

| Module | Responsibility | Consolidates (from the enterprise design) |
|---|---|---|
| **Auth & User Module** | Account management, auth, per-request `user_id` context | User & Session Service |
| **Knowledge Base Module** | File upload handling, write to local uploads directory, trigger parsing/chunking, topic CRUD, tag taxonomy, deep-dive merge decisions | Ingestion Service + Knowledge Base Service + Tagging & Metadata Service |
| **Question Bank Module** | Calls the Question & Tag Generation Agent, validates the structured response, persists questions + options + tags in one transaction | Question Generation Service + the generation-side half of the Tagging Service |
| **Exam Engine Module** | Exam session lifecycle, question selection (fixed set or tag-filtered), server-side timer, scoring, per-tag results aggregation | Exam Engine Service + Results & Analytics Service |

### 3.1 In-Process Background Worker
- Reads from a `jobs` table in Postgres (`pending` / `running` / `done` / `failed`).
- Runs ingestion (parsing → chunking → embedding → gap analysis) and generation (question + tag creation) as background tasks within the same process — using the web framework's native background-task support, not a separate worker fleet.
- This single component replaces the original design's separate Ingestion Job Queue, Generation Job Queue, and the dedicated workers behind them.

---

## 4. AI / LLM Agent Components

| Agent | Invoked By | Input | Output |
|---|---|---|---|
| **Ingestion & Knowledge Agent** | Knowledge Base Module (via background worker) | Raw extracted text + user's existing topic/tag graph | Semantic chunks, embeddings (written directly to `content_chunks.embedding` via `pgvector`), and a merge decision (existing topic vs. new topic) |
| **Question & Tag Generation Agent** | Question Bank Module (via background worker) | Context chunks, difficulty, count, user's existing tag vocabulary | A single structured JSON response containing MCQs (stem, options, correct answer, explanation) **and** their tag assignments together |

Both calls go directly from the backend application to the Anthropic API — there's no separate "AI layer service" to deploy; it's a library call from within the relevant module.

> The **Web Research Agent** is deferred — not part of this MVP's component list at all. Add it later as a third agent, called from the Knowledge Base Module, with zero impact on the other three components above.

---

## 5. Infrastructure / Platform Components (Lean)

| Component | MVP Choice |
|---|---|
| Database | Single PostgreSQL instance with the `pgvector` extension enabled (relational data + embeddings together) |
| File storage | A local directory on disk (e.g. `./data/uploads/`), served only through the application layer |
| Background processing | In-process async tasks + a `jobs` table — no Celery/Redis/SQS |
| Cache | None — exam session state lives directly in Postgres |
| Job status delivery | Simple polling endpoint (every few seconds) — no WebSocket/SSE infrastructure |
| Secrets | Environment variables / a local `.env` file for the LLM API key and DB credentials |
| Logging | Application-level logging to a local file or stdout — no centralized log aggregation needed yet |

Everything in this table is intentionally the simplest thing that works for one application instance and one database. The System Architecture document's "Migration Path" section spells out what each of these becomes if/when the deployment needs to grow.

---

## 6. Build Sequencing Suggestion

1. **Auth & User Module** + Auth UI — nothing else works without isolation context.
2. **Postgres schema** (per the Data Entity/Schema Design doc) with `pgvector` enabled, and the local uploads directory wired up.
3. **Knowledge Base Module** + `FileUploadInput`/`SyllabusTextInput` — get raw content into the system and onto disk.
4. **In-process background worker** + **Ingestion & Knowledge Agent** — turn uploaded content into chunks and embeddings.
5. **Question Bank Module** + **Question & Tag Generation Agent** — produce the first reusable, tagged questions.
6. **Exam Engine Module** + Exam Interface UI — close the loop to a working exam, including both modes.
7. **Results display** (folded into the Exam Engine Module) + Results UI.
8. **Deep-dive merge UX** (`DeepDiveConfirmationModal`) — once the linear MVP above works end-to-end.
9. *(Later, optional)* Web Research Agent, and — only if usage actually demands it — splitting any of the four modules into its own service per the migration path.
