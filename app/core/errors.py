from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from http import HTTPStatus
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None
    path: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


STATUS_ERROR_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "validation_error",
}


def error_response(
    status_code: int,
    message: str,
    *,
    code: str | None = None,
    details: list[dict[str, Any]] | None = None,
    path: str | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code=code or STATUS_ERROR_CODES.get(status_code, "error"),
            message=message,
            details=details,
            path=path,
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def api_error(
    status_code: int,
    message: str,
    *,
    code: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> HTTPException:
    detail: dict[str, Any] = {
        "code": code or STATUS_ERROR_CODES.get(status_code, "error"),
        "message": message,
    }
    if details:
        detail["details"] = details
    return HTTPException(status_code=status_code, detail=detail)


def normalize_lookup_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def validate_datetime_range(
    reported_from: datetime | None,
    reported_to: datetime | None,
) -> None:
    if reported_from and reported_to and reported_from > reported_to:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "reported_from must be less than or equal to reported_to",
        )


def validate_limit(limit: int, *, maximum: int = 100) -> None:
    if limit < 1 or limit > maximum:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"limit must be between 1 and {maximum}",
        )


def _normalize_http_exception_detail(detail: Any) -> tuple[str, str, list[dict[str, Any]] | None]:
    if isinstance(detail, dict):
        return (
            str(detail.get("code", "error")),
            str(detail.get("message", HTTPStatus.INTERNAL_SERVER_ERROR.phrase)),
            detail.get("details"),
        )
    if isinstance(detail, str):
        return "error", detail, None
    return "error", HTTPStatus.INTERNAL_SERVER_ERROR.phrase, None


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code, message, details = _normalize_http_exception_detail(exc.detail)
    return error_response(
        exc.status_code,
        message,
        code=STATUS_ERROR_CODES.get(exc.status_code, code) if code == "error" else code,
        details=details,
        path=request.url.path,
    )


def _flatten_validation_loc(loc: Sequence[Any]) -> str:
    return ".".join(str(part) for part in loc if part != "body")


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        {
            "field": _flatten_validation_loc(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "request validation failed",
        code="validation_error",
        details=details,
        path=request.url.path,
    )
