from fastapi import APIRouter

from app.api.v1.endpoints import (
    applications,
    documents,
    evaluations,
    health,
    jobs,
    profiles,
    reviews,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(applications.router)
api_v1_router.include_router(evaluations.router)
api_v1_router.include_router(profiles.router)
api_v1_router.include_router(reviews.router)
