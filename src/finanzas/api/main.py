"""Aplicación FastAPI. Capa HTTP delgada: los routers llaman a core.services."""

import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from finanzas import __version__
from finanzas.api.routers import accounts, health, imports, stats, transactions
from finanzas.shared.config import get_settings
from finanzas.shared.errors import (
    AlreadyImportedError,
    AppError,
    NotFoundError,
    ParserError,
    UnsupportedFormatError,
)
from finanzas.shared.logging import bind_correlation_id, configure_logging, get_logger

logger = get_logger("api")

# Red de seguridad: si un AppError escapa de un router sin mapear, la respuesta
# sigue siendo comprensible (mensaje + código), jamás un 500 críptico.
_STATUS_BY_ERROR: list[tuple[type[AppError], int]] = [
    (NotFoundError, 404),
    (UnsupportedFormatError, 415),
    (AlreadyImportedError, 409),
    (ParserError, 422),
    (AppError, 400),
]


def create_app() -> FastAPI:
    configure_logging(get_settings())
    app = FastAPI(title="Finanzas Personales API", version=__version__)
    app.include_router(health.router)
    app.include_router(accounts.router)
    app.include_router(imports.router)
    app.include_router(stats.router)
    app.include_router(transactions.router)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        status = next(s for cls, s in _STATUS_BY_ERROR if isinstance(exc, cls))
        logger.warning("app_error", code=exc.code, detail=exc.message, path=request.url.path)
        return JSONResponse(status_code=status, content={"detail": exc.message, "code": exc.code})

    @app.middleware("http")
    async def observability(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # correlation_id por request + timing (docs/10 §2-3).
        structlog.contextvars.clear_contextvars()
        cid = bind_correlation_id()
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Correlation-Id"] = cid
        return response

    return app


app = create_app()
