from datetime import datetime

from pydantic import BaseModel


class RouteOverview(BaseModel):
    route_id: int
    from_date: datetime
    to_date: datetime
    incident_count: int
    average_delay_minutes: float
    cancellation_count: int
    severe_incident_count: int
    reliability_score: float


class RouteWorstTime(BaseModel):
    route_id: int
    from_date: datetime
    to_date: datetime
    worst_hour: int | None
    incident_count: int
    average_delay_minutes: float
    cancellation_count: int
    disruption_score: float


class StationDelaySummary(BaseModel):
    station_id: int
    station_name: str
    city: str
    incident_count: int
    total_delay_minutes: int
    average_delay_minutes: float


class HourlyIncidentSummary(BaseModel):
    hour: int
    incident_count: int
    average_delay_minutes: float
    cancellation_count: int
