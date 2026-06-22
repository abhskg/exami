from fastapi import APIRouter
from app.api import auth, users, topics, documents, jobs

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(topics.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
