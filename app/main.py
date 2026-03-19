from fastapi import FastAPI

from app.core.config import get_settings
from app.routers.stations import router as stations_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

app.include_router(stations_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["meta"])
def read_root() -> dict[str, str]:
    return {
        "message": "Rail Reliability API",
        "docs_url": "/docs",
    }


@app.get("/health", tags=["meta"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
