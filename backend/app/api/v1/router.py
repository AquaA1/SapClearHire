from fastapi import APIRouter

from app.api.v1.endpoints import documents, health

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(documents.router)
