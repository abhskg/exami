import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.api import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging_config import setup_logging

# Initialize logging configuration
setup_logging()

logger = logging.getLogger("app.main")

# Import all models to ensure they are registered on the Base metadata
import app.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application...")
    # Initialize database tables for the Local-First MVP
    # Ensure pgvector extension is enabled first
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
    yield
    logger.info("Shutting down FastAPI application...")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Local-first MVP for AI-assisted ingestion, parsing, tag management, and exam practice.",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    path = request.url.path
    query_params = request.url.query
    full_path = f"{path}?{query_params}" if query_params else path
    client_host = request.client.host if request.client else "unknown"

    logger.info(f"Incoming request: {request.method} {full_path} from {client_host}")

    try:
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        logger.info(
            f"Completed request: {request.method} {full_path} - "
            f"Status {response.status_code} - "
            f"Duration: {duration:.3f}s"
        )
        return response
    except Exception as e:
        duration = time.perf_counter() - start_time
        logger.exception(
            f"Unhandled exception occurred while processing {request.method} {full_path}: {str(e)}"
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        f"HTTP exception on {request.method} {request.url.path}: "
        f"status_code={exc.status_code} detail={exc.detail}"
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        f"Request validation failed on {request.method} {request.url.path}: "
        f"errors={exc.errors()}"
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        f"Unhandled exception occurred while processing {request.method} {request.url.path}: {str(exc)}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
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
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
    }
