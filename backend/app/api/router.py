from fastapi import APIRouter

from app.api import (
    audit_routes,
    auth_routes,
    certificate_routes,
    health_routes,
    student_routes,
    verify_routes,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(health_routes.router)
api_router.include_router(auth_routes.router)
api_router.include_router(certificate_routes.router)
api_router.include_router(audit_routes.router)
api_router.include_router(student_routes.router)
api_router.include_router(verify_routes.router)