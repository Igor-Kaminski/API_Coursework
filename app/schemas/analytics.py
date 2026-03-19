from pydantic import BaseModel


class RouteReliabilityRead(BaseModel):
    route_id: int
    total_journeys: int
    on_time_percentage: float
    delayed_percentage: float
    cancelled_percentage: float


class RouteAverageDelayRead(BaseModel):
    route_id: int
    total_journeys: int
    average_delay_minutes: float


class DelayPatternPointRead(BaseModel):
    bucket: str
    total_journeys: int
    average_delay_minutes: float


class StationHotspotRead(BaseModel):
    station_id: int
    station_name: str
    affected_journeys: int
    average_delay_minutes: float


class IncidentFrequencyPointRead(BaseModel):
    bucket: str
    total_incidents: int


class DelayReasonFrequencyRead(BaseModel):
    reason: str
    total_occurrences: int


class UnresolvedLocationRead(BaseModel):
    station_id: int
    station_name: str
    unresolved_route_count: int


class RouteNameCoverageRead(BaseModel):
    total_routes: int
    fully_human_readable_routes: int
    partially_unresolved_routes: int
    fully_unresolved_routes: int
    unresolved_location_count: int
    top_unresolved_locations: list[UnresolvedLocationRead]
