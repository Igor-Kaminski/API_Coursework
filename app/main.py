from fastapi import FastAPI

from app.core.config import get_settings
from app.routers.analytics import router as analytics_router
from app.routers.incidents import router as incidents_router
from app.routers.routes import router as routes_router
from app.routers.stations import router as stations_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

app.include_router(stations_router, prefix=settings.api_v1_prefix)
app.include_router(routes_router, prefix=settings.api_v1_prefix)
app.include_router(incidents_router, prefix=settings.api_v1_prefix)
app.include_router(analytics_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["meta"])
def read_root() -> dict[str, str]:
    return {
        "message": "Rail Reliability API",
        "docs_url": "/docs",
    }


@app.get("/health", tags=["meta"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
