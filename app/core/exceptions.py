from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=404, detail=detail, error_code="not_found")


class ConflictError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=409, detail=detail, error_code="conflict")


class BadRequestError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=400, detail=detail, error_code="bad_request")


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
        },
    )
