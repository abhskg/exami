# Makefile for AI-Powered Exam Preparation Portal

.PHONY: help db-up db-down db-logs backend-setup backend-db-init backend-dev backend-test frontend-setup frontend-dev frontend-build setup-all dev clean

# Default shell
SHELL := /bin/sh

help:
	@echo "======================================================================"
	@echo "                AI-Powered Exam Preparation Portal                    "
	@echo "======================================================================"
	@echo "Available commands:"
	@echo "  make setup-all          - Complete setup (install dev dependencies, env files)"
	@echo "  make db-up              - Start PostgreSQL & pgvector via Docker"
	@echo "  make db-down            - Stop PostgreSQL container"
	@echo "  make db-logs            - Tail database container logs"
	@echo "  make backend-setup      - Set up Python virtual environment & dependencies"
	@echo "  make backend-db-init    - Initialize database schemas and extensions"
	@echo "  make backend-dev        - Start FastAPI development server (uvicorn)"
	@echo "  make backend-test       - Run pytest backend suite"
	@echo "  make frontend-setup     - Install frontend Node dependencies"
	@echo "  make frontend-dev       - Start Vite React development server"
	@echo "  make frontend-build     - Build frontend production bundles"
	@echo "  make dev                - Run backend and frontend concurrently"
	@echo "  make clean              - Clean temporary files, caches, and build folders"
	@echo "======================================================================"

# Docker database commands
db-up:
	docker compose up -d

db-down:
	docker compose down

db-logs:
	docker compose logs -f db

# Backend commands
backend-setup:
	@echo "Setting up Python virtual environment..."
	cd backend && python -m venv .venv
	@echo "To activate virtual environment manually, run: source backend/.venv/bin/activate (or backend\\.venv\\Scripts\\activate on Windows)"
	cd backend && .venv/bin/pip install -r requirements.txt || cd backend && .venv\\Scripts\\pip install -r requirements.txt

backend-db-init:
	cd backend && .venv/bin/python -m app.init_db || cd backend && .venv\\Scripts\\python -m app.init_db

backend-dev:
	cd backend && .venv/bin/uvicorn app.main:app --reload || cd backend && .venv\\Scripts\\uvicorn app.main:app --reload

backend-test:
	cd backend && .venv/bin/pytest || cd backend && .venv\\Scripts\\pytest

# Frontend commands
frontend-setup:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

# Composite/Helper commands
setup-all: db-up backend-setup frontend-setup
	@echo "======================================================================"
	@echo "Setup complete! Please configure backend/.env and frontend/.env."
	@echo "Then run 'make backend-db-init' to create the database tables."
	@echo "======================================================================"

dev:
	@echo "Starting backend and frontend dev servers concurrently..."
	@echo "Press Ctrl+C to stop both."
	make -j2 backend-dev frontend-dev

clean:
	@echo "Cleaning caches and temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".venv" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean completed."
