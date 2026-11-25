from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception with HTTP status and message."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def app_exception_handler(_: Request, exc: Any) -> JSONResponse:
    status_code = getattr(exc, "status_code", 400)
    message = getattr(exc, "message", str(exc))
    return JSONResponse(
        status_code=status_code,
        content={"detail": message, "success": False},
    )


async def http_exception_handler(_: Request, exc: Any) -> JSONResponse:
    status_code = getattr(exc, "status_code", 400)
    detail = getattr(exc, "detail", str(exc))
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "success": False},
    )



async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "success": False,
        },
    )
