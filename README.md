# 🎓 ExamI — Local-First MVP

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![VectorDB](https://img.shields.io/badge/VectorDB-pgvector-blue.svg?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)

Welcome to **ExamI**, a local-first MVP designed to provide individuals and small teams with a private, secure, and highly intelligent workspace for automated exam preparation. Powered by the Gemini API and robust local storage, the platform handles complex PDF/text parsing, dynamic multi-choice question (MCQ) generation, auto-tagging of topics, structured exam simulations, and performance analytics.

---

## 📸 Main Features

- **🔒 Complete Workspace Isolation**: User data is isolated at the API and database levels by `user_id` to guarantee secure workspaces.
- **🗂️ Full Topic Management**: Create, rename, and delete study topics directly from the sidebar. Deleting a topic cascades to remove all its documents, embeddings, questions, exam sessions, and tags in a single atomic operation. Rename uses an inline editor; delete triggers a confirmation modal to prevent accidental data loss.
- **📚 Fluid Knowledge Growth**: Ingest documents using three methods (File Upload, Raw Text Paste, and Web Search Agent simulation) to expand your knowledge base. Incoming content additive-merges into the existing relational model without overwriting older questions or tags.
- **🗃️ Open Knowledge Format (OKF) Ingestion**: Restructures document uploads and web crawls into a standardized OKF directory format (containing structured `index.md`, `log.md`, and dynamic concept clusters under `concepts/`) to enable graph-based semantic exploration.
- **🕸️ Interactive D3 Knowledge Graph**: Visualizes topic-specific knowledge bases as force-directed, zoomable, and interactive networks of concepts, complete with node details and connection graphs.
- **🔍 Staged Concept Review**: Provides a dedicated pipeline to review, refine, edit, and approve/reject generated concepts before final database vector serialization.
- **🚀 "Go Deeper" Concept Expansion**: Enables users to enrich existing knowledge nodes dynamically via targeted LLM queries, spawning sub-concepts and triggering automatic background re-vectorization.
- **🔄 Reparse & Ingestion Retry**: Resiliently handles processing failures, persisting query and search metadata configurations on disk for automated retries.
- **🧠 Intelligent Chunking & Embedding**: Extract text from files, raw text, or web scraping agent corpuses, parse into manageable segments, generate semantic vectors via the configured embedding provider (e.g. Gemini `gemini-embedding-001`), and store them using `pgvector`.
- **📝 Dynamic Structured Question Bank**: Automatically generate a customizable number of structured multiple-choice questions matching custom difficulties (`Easy`, `Medium`, `Hard`, `Mixed`) and tag them with concepts using the configured LLM API (e.g. Gemini `gemini-3.1-flash-lite`).

- **⏱️ Dual Exam Simulator Modes**:
    - _Practice Mode_: Provides **detailed, elaborated explanations** after each answer — covering why the correct answer is right, why each distractor is wrong (with misconception analysis), a real-world example or analogy, and any relevant formula or rule. Explanations are rendered as a rich colour-coded card (teal for correct, red for incorrect) with per-sentence visual hierarchy.
    - _Timed Mode_: Simulates standard test environments. Enforces hard countdown limits, locks answers, and hides explanation analytics until the exam is fully completed.
- **📊 Performance Heatmaps**: Deep insights mapped onto a customizable concept-tag hierarchy. Visualize weak points, score distribution, and overall preparation status.
- **🛡️ Centralized Logging & Error Resilience**: Structured console logger format matching `LOG_LEVEL` environment parameters. Centralized request intercepting middleware logs request parameters (method, path, client IP, status, duration) and catches all unhandled routing exceptions to log stack-traces and output clean 500 JSON responses.

---


## 🛠️ Technology Stack

| Component      | Technology                    | Description                                                                                                              |
| :------------- | :---------------------------- | :----------------------------------------------------------------------------------------------------------------------- |
| **Frontend**   | React (Vite + TypeScript)     | Responsive interface built with modern Vanilla CSS, glassmorphic styling foundations, and state persistence.             |
| **Backend**    | FastAPI (Python)              | High-performance async REST API with auto-generated OpenAPI documentation.                                               |
| **Database**   | PostgreSQL + `pgvector`       | Standard database engine configured to handle relational records alongside vector similarity dimensions (default: 768).  |
| **AI/LLM**     | Configurable LLM & Embeddings | Supports Gemini, OpenAI, LM Studio, or local servers. Embedded text vectorization and generation are dynamically routed. |
| **Task Queue** | FastAPI Background Tasks      | Light, in-process async background task worker managing ingestion queues and job tracking states.                        |
| **Storage**    | Local Filesystem              | Raw files and documents organized under `./data/uploads/{user_id}/`.                                                     |

---

## 📂 Project Structure

```
ai-exam-portal/
├── backend/                  # Python FastAPI Application
│   ├── app/                  # Main application source code
│   │   ├── api/              # API router endpoints (auth, questions, exams, ingestion, knowledge)
│   │   ├── core/             # Configuration, security, database engines
│   │   ├── models/           # SQLAlchemy schemas (users, topics, tags, questions, etc.)
│   │   ├── schemas/          # Pydantic schemas for validation & serialization
│   │   ├── services/         # Business logic (Vector Query, MCQ Ingestion, Exam Engine, OKF)
│   │   ├── workers/          # In-process background task runners
│   │   └── main.py           # Application entry point & FastAPI setup
│   ├── requirements.txt      # Python dependencies
│   ├── pyproject.toml        # Ruff/Pytest/Black configurations [NEW]
│   └── .env.example          # Sample environment variables
│
├── frontend/                 # React Frontend Client (Vite + TS)
│   ├── src/
│   │   ├── components/       # Reusable modular UI widgets
│   │   │   └── knowledge/    # D3 Knowledge Graph, Concept Detail, and Staged Review Panels [NEW]
│   │   ├── pages/            # View pages (Login, Setup, Exam, Results)
│   │   ├── hooks/            # Shared custom React hooks
│   │   ├── services/         # API HTTP communication layer
│   │   ├── App.tsx           # Application entry UI shell
│   │   └── main.tsx          # Client-side entry script
│   ├── package.json          # Node dependencies
│   ├── tsconfig.json         # TypeScript configuration
│   ├── .prettierrc           # Prettier configuration [NEW]
│   └── vite.config.ts        # Vite configuration script
│
├── data/                     # Local filesystem storage (Git ignored)
│   ├── uploads/              # Raw files (PDFs, text) stored by user_id
│   ├── knowledge/            # OKF markdown concept files, indexes, and logs [NEW]
│   └── staging/              # Staged OKF concepts awaiting review [NEW]
│
├── system-docs/              # System architecture, data schemas, and UI flows
├── .editorconfig             # Editor format configurations [NEW]
├── docker-compose.yml        # PostgreSQL + pgvector Docker setup
├── Makefile                  # Unix/Dev Command runner [NEW]
├── run.ps1                   # Windows Native PowerShell runner [NEW]
├── README.md                 # Project Overview (This file)
└── changelog.md              # Log of iterations and changes
```

---

## ⚡ Quick Start

You can quickly configure, setup, and run the project using our new developer support scripts:

### Standard Command Quick-Reference

| Task                   | Unix / Linux (`make`)  | Windows Native (`PowerShell`) |
| :--------------------- | :--------------------- | :---------------------------- |
| **All-in-One Setup**   | `make setup-all`       | `.\run.ps1 setup`             |
| **Start Database**     | `make db-up`           | `.\run.ps1 db-up`             |
| **Stop Database**      | `make db-down`         | `.\run.ps1 db-down`           |
| **Initialize Schema**  | `make backend-db-init` | `.\run.ps1 backend-db-init`   |
| **Run Dev Servers**    | `make dev`             | `.\run.ps1 dev`               |
| **Run Backend Tests**  | `make backend-test`    | `.\run.ps1 backend-test`      |
| **Format Code**        | `make format`          | `.\run.ps1 format`            |
| **Clean Build Caches** | `make clean`           | `.\run.ps1 clean`             |
| **Purge Documents**    | `make purge-documents` | `.\run.ps1 purge-documents`   |
| **Purge Questions**    | `make purge-questions` | `.\run.ps1 purge-questions`   |
| **Purge Tags**         | `make purge-tags`      | `.\run.ps1 purge-tags`        |
| **Purge Topics**       | `make purge-topics`    | `.\run.ps1 purge-topics`      |
| **Purge All Data**     | `make purge-all`       | `.\run.ps1 purge-all`         |

---

### Step-by-Step Manual Setup

If you prefer to configure components manually, follow these steps:

#### 1. Database Setup

Start the local PostgreSQL database with `pgvector` mapping to port `5434` (to avoid conflicts with native PostgreSQL installations):

```bash
docker compose up -d
```

#### 2. Backend Setup

1.  Navigate to the `backend/` directory:
    ```bash
    cd backend
    ```
2.  Create and activate a Python virtual environment:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Copy the `.env.example` to `.env` and fill in the required API keys (specifically `GEMINI_API_KEY` and the `DATABASE_URL` targeting port `5434`):
    ```bash
    cp .env.example .env
    ```
5.  Initialize database schemas and compile extensions:
    ```bash
    python -m app.init_db
    ```
6.  Start the development server:
    ```bash
    uvicorn app.main:app --reload
    ```

#### 3. Frontend Setup

1.  Navigate to the `frontend/` directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies and copy environmental configuration template:
    ```bash
    npm install
    ```
3.  Copy the `.env.example` to `.env` and configure `VITE_MAX_FILE_SIZE_MB` if a different upload limit is desired (default: `15`):
    ```bash
    cp .env.example .env
    ```
4.  Start the Vite React development server:
    ```bash
    npm run dev
    ```

---

## 📖 Usage Guide

Follow this step-by-step guide to get the most out of ExamI's local-first knowledge cataloging and simulator capabilities:

### 1. Create a Study Topic
- Launch the application and register/log in.
- In the left sidebar, click the **Create Topic** input field, type a topic name (e.g., "Software Engineering"), and press Enter.
- *Tip*: You can rename topics inline by hovering and clicking the ✏️ icon, or delete topics by clicking the 🗑️ icon.

### 2. Ingest Reference Documents & Web Search Corpuses
Choose one of three ingestion workflows to expand your knowledge base under the active topic:
- **File Ingestion**: Drag & drop or browse for TXT, MD, or PDF documents (up to 15MB) and upload them.
- **Raw Text Paste**: Paste raw notes, course descriptions, or chapters directly into the text editor.
- **Web Search Ingestion**: Feed a syllabus and search topics into the intelligent Web Scraping agent. The agent scrapes matching search targets up to **30k characters** of relevant corpus context.
  
  *Recommended Syllabus & Topics Generator Prompt*: Use the prompt below with your favorite LLM to format the syllabus and topics list for the web search inputs:
  ```text
  Act as an expert curriculum designer and exam specialist. I am drafting a multiple-choice question (MCQ) exam and need a structured syllabus layout. 

  For the exam/subject specified below, please generate two distinct, comma-separated lists. 

  Exam: [Insert Exam Name/Subject Here]

  Please provide the output exactly in the following format:

  Syllabus: <Provide a comma-separated list of the main, high-level modules or chapters for this exam>

  List of Topics to follow upon with detailed drilled down: <Provide a comprehensive, comma-separated list of the specific sub-topics, concepts, and key terms nested under those main modules that are critical for an MCQ-style test>
  ```

### 3. Review Staged Concepts
For web search ingestion and structured syllabus flows:
- The system stages extracted concepts in a **Review Panel** instead of immediately committing them.
- Review the concept names, summaries, and hierarchies. Approve, reject, or modify concepts inline.
- Click **Save Approved Concepts** to compile them into Open Knowledge Format (OKF) files, chunk them along semantic boundaries, generate embeddings, and save them in the vector database.

### 4. Explore the Interactive D3 Knowledge Graph
- Switch to the **Knowledge Catalog** tab in the main view.
- Open the **Knowledge Graph** sub-tab to visualize your concepts as a D3 force-directed network.
- Click on any concept node to pull up the **Concept Detail Panel** showing the full markdown content.
- To expand any node, write a query or paste text in the **"Go Deeper"** text box at the bottom of the details pane. The system will automatically update the concept content and trigger background tasks to re-vectorize the text chunks.

### 5. Generate and Customize MCQ Practice Exams
- Navigate to the **Exam Simulator** tab.
- Set up a customized question pool:
  - Select your target study topic.
  - Choose a target question count (1 to 30 MCQs).
  - Select a difficulty level (`Easy`, `Medium`, `Hard`, or `Mixed`).
  - Optionally select specific concept tags/chips to filter the source chunks.
- Click **Generate Questions** to query pgvector and synthesize structured MCQs with detailed explanations.

### 6. Take Mock Examinations
Choose between two simulation formats to test your knowledge:
- **Practice Mode**: Enables immediate feedback. As soon as you select an answer, the simulator displays a detailed, sentence-highlighted breakdown of:
  - Correct choice rationale.
  - Distractor/misconception analysis for incorrect choices.
  - Real-world analogies or code examples.
- **Timed Mode**: Replicates realistic test environments. Enforces strict countdown timers, locks responses upon selection, and displays complete scorecards, statistics, and reviews only after the test has been submitted.

---

## 🤖 Swapping LLM Providers & Models

You can configure which LLM provider to use for generating questions and text embeddings by editing the `backend/.env` file. The application supports **Gemini**, **OpenAI**, and **LMStudio (Local Keyless)**.

### Configuration Settings

The following variables in `backend/.env` control the active providers and limits:

| Variable             | Description                       | Allowed Values / Examples                                   |
| :------------------- | :-------------------------------- | :---------------------------------------------------------- |
| `LLM_PROVIDER`       | Provider for MCQ generation       | `gemini` (default), `openai`, `lmstudio`                    |
| `LLM_MODEL`          | Specific model for MCQ generation | `gemini-3.1-flash-lite`, `gpt-4o-mini`, custom local model       |
| `EMBEDDING_PROVIDER` | Provider for text embeddings      | `gemini` (default), `openai`, `lmstudio`, `mock`            |
| `EMBEDDING_MODEL`    | Model used for vector embeddings  | `gemini-embedding-001` (default), `text-embedding-3-small`, local model |
| `MAX_FILE_SIZE_MB`   | Maximum allowed file upload size  | Integer value in MB (default: `15`)                         |

### Example Configurations

#### 1. Google Gemini (Default)

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.1-flash-lite
GEMINI_API_KEY="your-gemini-api-key"

EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-001
```

#### 2. OpenAI

When using OpenAI, the vector output of `text-embedding-3-*` models is automatically configured or normalized (padded/truncated) to **768 dimensions** to align with the database schema.

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY="sk-proj-..."

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

#### 3. LMStudio (Local Offline Mode)

Make sure LMStudio's local server is running. No API keys are required for local providers.

```env
LLM_PROVIDER=lmstudio
LLM_MODEL="your-loaded-model-name"
LMSTUDIO_BASE_URL="http://localhost:1234/v1"

EMBEDDING_PROVIDER=lmstudio
EMBEDDING_MODEL="nomic-embed-text-v1.5"
```

---

## 🧪 Testing

The backend includes a comprehensive pytest suite covering configuration, encryption, JWT tokens, user authentication, PDF/text ingestion, background workers, pgvector queries, question generation, and exam engines.

To run the tests:

```bash
# Using Makefile
make backend-test

# Using PowerShell (Windows)
.\run.ps1 backend-test

# Manually in backend/ directory
cd backend
.venv/bin/pytest -v
```

---

## 📄 Design & Architecture Docs

For in-depth details of design architectures, database tables, and client state mappings, please review:

- [System Architecture](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/01-system-architecture.md)
- [User Journeys & Flows](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/02-user-flow-journey-maps.md)
- [Data Entity & Database Schema](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/03-data-schema-design.md)
- [Component Breakdown](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/04-component-breakdown.md)
