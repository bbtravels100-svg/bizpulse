import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .correlation import get_correlation_id

logger = logging.getLogger("bizpulse.errors")


def register_error_handlers(app: FastAPI) -> None:
    """Register safe, correlation-aware error handlers across the application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        cid = get_correlation_id()
        headers = dict(exc.headers) if exc.headers else {}
        headers["X-Correlation-ID"] = cid

        # Keep safe detail for client
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "correlation_id": cid,
            },
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        cid = get_correlation_id()
        logger.warning(
            f"Request validation failed on {request.method} {request.url.path}: {exc.errors()}",
            extra={"correlation_id": cid, "endpoint": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Request payload validation failed",
                "errors": exc.errors(),
                "correlation_id": cid,
            },
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        cid = get_correlation_id()
        # Log full traceback server-side only
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
            extra={"correlation_id": cid, "endpoint": request.url.path},
        )
        # Return generic safe message to client - never leak internal stack traces or paths
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred. Please reference the correlation ID when contacting support.",
                "correlation_id": cid,
            },
            headers={"X-Correlation-ID": cid},
        )
