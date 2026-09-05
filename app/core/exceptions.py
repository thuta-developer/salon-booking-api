"""Application-level exception types and FastAPI exception handlers.

Usage:
    from app.core.exceptions import NotFoundError

    raise NotFoundError("User not found")
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status


class AppException(Exception):
    """App-level base exception. Subclasses set `status_code` / `detail`."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Application error"
    headers: dict | None = None

    def __init__(self, detail: str | None = None, headers: dict | None = None):
        if detail is not None:
            self.detail = detail
        if headers is not None:
            self.headers = headers
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"


class DuplicateError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Resource already exists"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Unauthorized"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Forbidden"


class ValidationFailedError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation failed"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that convert ``AppException`` subclasses to JSON responses."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )