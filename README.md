# 🎓 AI-Powered Exam Preparation Portal — Local-First MVP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![VectorDB](https://img.shields.io/badge/VectorDB-pgvector-blue.svg?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)

Welcome to the **AI-Powered Exam Preparation Portal**, a local-first MVP designed to provide individuals and small teams with a private, secure, and highly intelligent workspace for automated exam preparation. Powered by the Gemini API and robust local storage, the platform handles complex PDF/text parsing, dynamic multi-choice question (MCQ) generation, auto-tagging of topics, structured exam simulations, and performance analytics.

---

## 📸 Main Features

- **🔒 Complete Workspace Isolation**: User data is isolated at the API and database levels by `user_id` to guarantee secure workspaces.
- **📚 Fluid Knowledge Growth**: Ingest documents using three methods (File Upload, Raw Text Paste, and Web Search Agent simulation) to expand your knowledge base. Incoming content additive-merges into the existing relational model without overwriting older questions or tags.
- **🧠 Intelligent Chunking & Embedding**: Extract text from files, raw text, or web scraping agent corpuses, parse into manageable segments, generate semantic vectors via the configured embedding provider (e.g. Gemini `text-embedding-004`), and store them using `pgvector`.
- **📝 Dynamic Structured Question Bank**: Automatically generate structured multiple-choice questions matching custom difficulties (`Easy`, `Medium`, `Hard`, `Mixed`) and tag them with concepts using the configured LLM API (e.g. Gemini `gemini-2.0-flash`).
- **⏱️ Dual Exam Simulator Modes**:
    - _Practice Mode_: Provides instant explanations and correction feedback as you complete each question.
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
│   │   ├── api/              # API router endpoints (auth, questions, exams, ingestion)
│   │   ├── core/             # Configuration, security, database engines
│   │   ├── models/           # SQLAlchemy schemas (users, topics, tags, questions, etc.)
│   │   ├── schemas/          # Pydantic schemas for validation & serialization
│   │   ├── services/         # Business logic (Vector Query, MCQ Ingestion, Exam Engine)
│   │   ├── workers/          # In-process background task runners
│   │   └── main.py           # Application entry point & FastAPI setup
│   ├── requirements.txt      # Python dependencies
│   ├── pyproject.toml        # Ruff/Pytest/Black configurations [NEW]
│   └── .env.example          # Sample environment variables
│
├── frontend/                 # React Frontend Client (Vite + TS)
│   ├── src/
│   │   ├── components/       # Reusable modular UI widgets
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
│   └── uploads/              # Raw files (PDFs, text) stored by user_id
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
| **Clean Build Caches** | `make clean`           | `.\run.ps1 clean`             |
| **Purge Documents**    | `make purge-documents` | —                             |
| **Purge Questions**    | `make purge-questions` | —                             |
| **Purge Tags**         | `make purge-tags`      | —                             |
| **Purge Topics**       | `make purge-topics`    | —                             |
| **Purge All Data**     | `make purge-all`       | —                             |

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
    cp .env.example .env
    ```
3.  Start the Vite React development server:
    ```bash
    npm run dev
    ```

---

## 🤖 Swapping LLM Providers & Models

You can configure which LLM provider to use for generating questions and text embeddings by editing the `backend/.env` file. The application supports **Gemini**, **OpenAI**, and **LMStudio (Local Keyless)**.

### Configuration Settings

The following variables in `backend/.env` control the active providers:

| Variable             | Description                       | Allowed Values / Examples                                   |
| :------------------- | :-------------------------------- | :---------------------------------------------------------- |
| `LLM_PROVIDER`       | Provider for MCQ generation       | `gemini` (default), `openai`, `lmstudio`                    |
| `LLM_MODEL`          | Specific model for MCQ generation | `gemini-2.0-flash`, `gpt-4o-mini`, custom local model       |
| `EMBEDDING_PROVIDER` | Provider for text embeddings      | `gemini` (default), `openai`, `lmstudio`, `mock`            |
| `EMBEDDING_MODEL`    | Model used for vector embeddings  | `text-embedding-004`, `text-embedding-3-small`, local model |

### Example Configurations

#### 1. Google Gemini (Default)

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GEMINI_API_KEY="your-gemini-api-key"

EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=text-embedding-004
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
