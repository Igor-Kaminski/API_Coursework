from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import IncidentStatus, IncidentType, Severity


class IncidentBase(BaseModel):
    route_id: int = Field(gt=0)
    station_id: int | None = Field(default=None, gt=0)
    incident_type: IncidentType
    severity: Severity
    status: IncidentStatus = IncidentStatus.open
    title: str = Field(min_length=3, max_length=160)
    description: str | None = None
    delay_minutes: int | None = Field(default=None, ge=0)
    occurred_at: datetime
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> "IncidentBase":
        if self.resolved_at and self.resolved_at < self.occurred_at:
            raise ValueError("resolved_at must be greater than or equal to occurred_at.")
        if self.status == IncidentStatus.resolved and self.resolved_at is None:
            raise ValueError("resolved incidents must include resolved_at.")
        return self


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(IncidentBase):
    pass


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_status(self) -> "IncidentStatusUpdate":
        if self.status == IncidentStatus.resolved and self.resolved_at is None:
            raise ValueError("resolved incidents must include resolved_at.")
        return self


class IncidentRead(IncidentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
