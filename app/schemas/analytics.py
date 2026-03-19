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


class RouteCancellationRateRead(BaseModel):
    route_id: int
    total_journeys: int
    cancelled_journeys: int
    cancellation_rate_percentage: float


class DelayDistributionBucketRead(BaseModel):
    bucket: str
    total_journeys: int
    percentage: float


class RouteDelayDistributionRead(BaseModel):
    route_id: int
    total_journeys: int
    buckets: list[DelayDistributionBucketRead]


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


class IncidentBreakdownPointRead(BaseModel):
    label: str
    total_incidents: int


class DelayReasonFrequencyRead(BaseModel):
    reason: str
    total_occurrences: int


class TopDelayedRouteRead(BaseModel):
    route_id: int
    route_name: str
    route_code: str | None
    total_journeys: int
    average_delay_minutes: float


class TopCancelledRouteRead(BaseModel):
    route_id: int
    route_name: str
    route_code: str | None
    total_journeys: int
    cancelled_journeys: int
    cancellation_rate_percentage: float


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
