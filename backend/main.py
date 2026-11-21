"""FastAPI entry point:  uvicorn main:app --reload --port 8000"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.blockchain.contract_service import build_chain_client
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.logging_config import configure_logging
from app.services.auth_service import ensure_admin
from app.utils.exceptions import AppError

log = logging.getLogger("ecv")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    if settings.admin_password:
        with SessionLocal() as db:
            ensure_admin(db, settings.admin_username, settings.admin_password)
        log.info("Administrator account '%s' is ready.", settings.admin_username)
    else:
        log.warning("ADMIN_PASSWORD is empty: no administrator account was created.")

    # Connects lazily, so the API starts even if the blockchain node is not running yet.
    app.state.chain = build_chain_client()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    app.include_router(api_router)
    return app


app = create_app()