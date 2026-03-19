from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import ORMModel, TimestampedResponse

IncidentSeverity = Literal["low", "medium", "high", "critical"]
IncidentStatus = Literal["open", "investigating", "resolved", "closed"]


class IncidentBase(ORMModel):
    route_id: int | None = None
    station_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    incident_type: str = Field(min_length=1, max_length=100)
    severity: IncidentSeverity
    status: IncidentStatus = "open"
    reported_at: datetime

    @model_validator(mode="after")
    def validate_location_scope(self) -> "IncidentBase":
        if self.route_id is None and self.station_id is None:
            raise ValueError("either route_id or station_id must be provided")
        return self


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(ORMModel):
    route_id: int | None = None
    station_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    incident_type: str | None = Field(default=None, min_length=1, max_length=100)
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    reported_at: datetime | None = None

    @model_validator(mode="after")
    def validate_location_scope(self) -> "IncidentUpdate":
        if self.route_id is None and self.station_id is None:
            return self
        return self


class IncidentRead(TimestampedResponse, IncidentBase):
    pass
