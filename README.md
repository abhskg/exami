# AI-Powered Exam Preparation Portal — Local-First MVP

Welcome to the **AI-Powered Exam Preparation Portal**, designed as a lean, local-first MVP. This application provides a single-user / small-team environment for automated exam preparation powered by LLMs. It features in-process background parsing, dynamic question generation, auto-tagging, exam simulation, and granular review analytics.

---

## 🚀 Key Features (Local-First MVP)

1. **User Isolation**: All data is scoped at the API and database query levels by `user_id` to guarantee secure workspaces.
2. **Fluid Knowledge Growth**: Support for uploading content that additive-merges into the existing knowledge base, expanding topics dynamically without overwriting old questions or tags.
3. **Smart Ingestion & Chunking**: Automatically processes uploaded PDFs/texts, extracts knowledge, produces embeddings, and maps them to topics.
4. **Interactive MCQs & Auto-Tagging**: Generates structured multiple-choice questions matching custom difficulties (`easy`, `medium`, `hard`) and tags them with concepts using the Gemini API.
5. **Dual Exam Modes**:
   - **Practice Mode**: Immediate feedback and detailed explanations per question.
   - **Timed Mode**: Strictly enforced time-limit with locked answers and detailed results shown only after submission.
6. **Performance Heatmaps**: Summarizes overall scores and maps strengths/weaknesses across the custom tag hierarchy.

---

## 🛠️ Technology Stack

* **Frontend**: React (Vite + TypeScript) + CSS (Vanilla/Modern)
* **Backend**: FastAPI (Python)
* **Database**: PostgreSQL with `pgvector` (Stores both relational structures and vector embeddings)
* **AI/LLM**: Gemini API (via Google GenAI SDK)
* **Background Processing**: FastAPI In-Process Async Tasks + SQL Job Queue
* **File Storage**: Local Filesystem Storage (`./data/uploads/{user_id}/...`)

---

## 📂 Project Structure

```
ai-exam-portal/
├── backend/                  # Python FastAPI Application
│   ├── app/                  # Main application source code
│   │   ├── api/              # API router endpoints (auth, topic, exam, ingestion)
│   │   ├── core/             # Configuration, security, database settings
│   │   ├── models/           # SQLAlchemy schemas (users, topics, tags, questions, etc.)
│   │   ├── schemas/          # Pydantic schemas for request validation & API responses
│   │   ├── services/         # Business logic (Ingestion, Question Generation, Exam Engine)
│   │   ├── workers/          # In-process background task runners
│   │   └── main.py           # Application entry point & FastAPI setup
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Sample environment variables
│
├── frontend/                 # React Frontend Client (Vite + TS)
│   ├── src/
│   │   ├── components/       # Reusable modular components
│   │   ├── pages/            # View pages (Login, Dashboard, Setup, Exam, Results)
│   │   ├── hooks/            # Shared custom React hooks
│   │   ├── services/         # API HTTP communication layer
│   │   ├── App.tsx           # Application entry UI shell
│   │   └── main.tsx          # Client side entry script
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite configuration script
│
├── data/                     # Local filesystem storage (Git ignored)
│   └── uploads/              # Raw files (PDFs, text) stored by user_id
│
├── system-docs/              # System architecture, data schemas, journeys & component breakdowns
│
├── docker-compose.yml        # Multi-container orchestration for PostgreSQL + pgvector
├── .gitignore                # Target directories, environments & config files to exclude from Git
├── README.md                 # This file
└── changelog.md              # Log of changes and iterations
```

---

## ⚡ Quick Start

### 1. Database Setup
Start the local PostgreSQL database with `pgvector`:
```bash
docker compose up -d
```

### 2. Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the `.env.example` to `.env` and fill in the required API keys (e.g., Gemini API key, Postgres connection credentials).
5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 3. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```

---

## 📄 Design & Architecture Docs
For more comprehensive guides on how each subsystem interacts, please review:
* [System Architecture](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/01-system-architecture.md)
* [User Journeys & Flows](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/02-user-flow-journey-maps.md)
* [Data Entity & Database Schema](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/03-data-schema-design.md)
* [Component Breakdown](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/system-docs/04-component-breakdown.md)
