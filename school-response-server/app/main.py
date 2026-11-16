"""
app/main.py
===========
FastAPI application factory.

Architecture:
  Internet / LAN
       ↓
   FastAPI  (this file)
       ↓
   PostgreSQL  (via SQLAlchemy async)

Security features enabled:
  - JWT authentication (role determined server-side)
  - CORS restricted to configured origins
  - Request size limits
  - Structured audit logging
  - Global exception handlers with consistent error envelope
  - Rate limiting on auth endpoints
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import PlickersException
from app.core.logging import setup_logging
from app.core.rate_limit import limiter

# ── Logging ────────────────────────────────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy import text
    from app.db.session import engine

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # ── Verify database connectivity ───────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection: OK")
    except Exception as exc:
        logger.error(f"Database connection FAILED: {exc}")
        raise

    yield

    logger.info("Server shutting down")
    await engine.dispose()
    logger.info("Database engine disposed")


# ── App factory ────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Secure, multi-tenant school classroom response system backend. "
            "Manages schools, students, ArUco response cards, quizzes, and live scanner responses.\n\n"
            "**Authentication:** Bearer JWT token via `/api/v1/auth/login`\n\n"
            "**Card System:** marker_id == card_number (ArUco DICT_6X6_250)\n\n"
            "**Scanner flow:** POST `/api/v1/scanner/responses` → WebSocket `/ws/quiz/{id}`"
        ),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Rate limiting ──────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── CORS ──────────────────────────────────────────────────────────────
    cors_kwargs = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if settings.APP_ENV == "development":
        cors_kwargs["allow_origin_regex"] = r"^https?://.*"
    else:
        cors_kwargs["allow_origins"] = [o for o in settings.cors_origins_list if o != "*"]

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    # ── Request size limit ────────────────────────────────────────────────
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_upload_size_bytes)

    # ── Secure headers ────────────────────────────────────────────────────
    app.add_middleware(SecureHeadersMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────
    _register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────
    _register_routers(app)

    return app


def _register_routers(app: FastAPI) -> None:
    from app.api.v1.auth import router as auth_router
    from app.api.v1.schools import router as schools_router
    from app.api.v1.academic_years import router as academic_router
    from app.api.v1.teachers import router as teachers_router
    from app.api.v1.students import router as students_router
    from app.api.v1.cards import router as cards_router
    from app.api.v1.questions import router as questions_router
    from app.api.v1.quiz_sessions import router as quiz_router
    from app.api.v1.scanner import router as scanner_router
    from app.api.v1.reports import router as reports_router
    from app.api.v1.admin import router as admin_router

    PREFIX = "/api/v1"

    # ── Global (no school_id path param) ──────────────────────────────────
    app.include_router(auth_router, prefix=PREFIX)
    app.include_router(schools_router, prefix=PREFIX)
    app.include_router(scanner_router, prefix=PREFIX)

    # ── School-scoped (school_id path param) ──────────────────────────────
    SCHOOL = PREFIX + "/schools/{school_id}"
    app.include_router(academic_router, prefix=SCHOOL)
    app.include_router(teachers_router, prefix=SCHOOL)
    app.include_router(students_router, prefix=SCHOOL)
    app.include_router(cards_router, prefix=SCHOOL)
    app.include_router(questions_router, prefix=SCHOOL)
    app.include_router(quiz_router, prefix=SCHOOL)
    app.include_router(reports_router, prefix=SCHOOL)
    app.include_router(admin_router, prefix=SCHOOL)

    # ── Health check ──────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], summary="Health check")
    async def health() -> dict:
        return {"status": "ok", "version": settings.APP_VERSION}

    # ── WebSocket for Live Quiz ──────────────────────────────────────────
    from fastapi import WebSocket, WebSocketDisconnect
    from app.websocket.manager import ws_manager

    @app.websocket("/ws/quiz/{quiz_session_id}")
    async def global_quiz_websocket(websocket: WebSocket, quiz_session_id: int) -> None:
        await ws_manager.connect(websocket, quiz_session_id)
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            pass
        finally:
            await ws_manager.disconnect(websocket, quiz_session_id)

    @app.get("/", tags=["System"], summary="API root")
    async def root() -> dict:
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }



def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlickersException)
    async def plickers_exception_handler(request: Request, exc: PlickersException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": jsonable_encoder(exc.errors()),
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                },
            },
        )


# ── Custom middleware ──────────────────────────────────────────────────────

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding the configured body size limit."""

    def __init__(self, app: Any, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "success": False,
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": f"Request body exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
                    },
                },
            )
        return await call_next(request)


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        return response


# ── Entry point ────────────────────────────────────────────────────────────
app = create_app()
