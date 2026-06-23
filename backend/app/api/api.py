from fastapi import APIRouter

from app.api import auth, documents, exams, jobs, questions, topics, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(topics.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(questions.router)
api_router.include_router(exams.router)
