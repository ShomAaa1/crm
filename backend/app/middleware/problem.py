"""RFC 7807 Problem Details — единый формат ошибок.

Все handlers возвращают JSON по схеме:
{
  "type": "about:blank",
  "title": "...",
  "status": <int>,
  "detail": "...",
  "instance": "<request path>",
  "errors": [...]   # опционально (например, для 422)
}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("autodetail.problem")

PROBLEM_MEDIA = "application/problem+json"


class ProblemException(Exception):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str | None = None,
        type_: str = "about:blank",
        extras: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type = type_
        self.extras = extras or {}
        super().__init__(detail or title)


def _problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str | None = None,
    type_: str = "about:blank",
    extras: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "instance": str(request.url.path),
    }
    if detail:
        body["detail"] = detail
    if extras:
        body.update(extras)
    return JSONResponse(content=body, status_code=status_code, media_type=PROBLEM_MEDIA)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemException)
    async def problem_handler(request: Request, exc: ProblemException) -> JSONResponse:
        return _problem_response(
            request,
            status_code=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            type_=exc.type,
            extras=exc.extras,
        )

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return _problem_response(
            request,
            status_code=exc.status_code,
            title=_default_title(exc.status_code),
            detail=str(exc.detail) if exc.detail else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail="Запрос содержит ошибки валидации",
            extras={"errors": exc.errors()},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("IntegrityError: %s", exc)
        return _problem_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail="Нарушение ограничения целостности БД",
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error: %s", exc)
        return _problem_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Database error",
            detail="Ошибка работы с базой данных",
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return _problem_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal Server Error",
            detail="Внутренняя ошибка сервера",
        )


_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
}


def _default_title(code: int) -> str:
    return _TITLES.get(code, "Error")
