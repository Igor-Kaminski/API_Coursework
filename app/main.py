from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler


settings = get_settings()

app = FastAPI(
    title=settings.project_name,
    version=settings.project_version,
    description=(
        "An incident-driven API for managing transport routes, stations, and "
        "delay analytics across a curated transport network."
    ),
)
app.add_exception_handler(AppError, app_error_handler)


@app.get("/health", tags=["Utility"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
