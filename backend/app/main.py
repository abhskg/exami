from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.api import api_router

# Import all models to ensure they are registered on the Base metadata
from app.models.user import User

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables for the Local-First MVP
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Local-first MVP for AI-assisted ingestion, parsing, tag management, and exam practice.",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS configuration for React frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints under /api
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": f"Welcome to the {settings.APP_NAME} API",
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.APP_ENV
    }
