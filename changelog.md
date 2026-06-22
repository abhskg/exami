# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Settings Loader (Task 1.1)**: Added a configuration loader utilizing `pydantic-settings` to dynamically parse and validate environments from a `.env` file, and integrated it into `backend/app/main.py`.
- **Validation Tests**: Introduced configuration and validation tests under `backend/app/tests/test_config.py`.
- **SQLAlchemy Connection Pool (Task 1.2)**: Initialized SQLAlchemy connection pool engine with standard local settings (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`) in `backend/app/core/database.py` and implemented the FastAPI dependency generator `get_db()`.

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

