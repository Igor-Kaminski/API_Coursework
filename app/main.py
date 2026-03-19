from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import dispose_engine, ping_database
from app.core.errors import (
    api_error,
    database_exception_handler,
    http_exception_handler,
    rate_limit_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.routers.analytics import router as analytics_router
from app.routers.incidents import router as incidents_router
from app.routers.routes import router as routes_router
from app.routers.stations import router as stations_router

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"], headers_enabled=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ping_database()
    app.state.startup_checks = {"database": "ok"}
    try:
        yield
    finally:
        dispose_engine()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
    try:
        ping_database()
    except SQLAlchemyError as exc:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "database unavailable",
            details=[{"field": "database", "message": str(exc.__class__.__name__)}],
        ) from exc

    return {"status": "ok", "database": "ok"}
