from fastapi import APIRouter

from app.api.v1.endpoints import analytics, incidents, routes, stations


api_router = APIRouter()
api_router.include_router(stations.router, prefix="/stations", tags=["Stations"])
api_router.include_router(routes.router, prefix="/routes", tags=["Routes"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
