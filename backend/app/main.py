from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Local-first MVP for AI-assisted ingestion, parsing, tag management, and exam practice.",
    version="0.1.0",
    debug=settings.DEBUG
)

# CORS configuration for React frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
