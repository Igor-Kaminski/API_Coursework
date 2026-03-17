from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import TransportMode


class RouteBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    origin_station_id: int = Field(gt=0)
    destination_station_id: int = Field(gt=0)
    transport_mode: TransportMode
    active: bool = True

    @model_validator(mode="after")
    def validate_endpoints(self) -> "RouteBase":
        if self.origin_station_id == self.destination_station_id:
            raise ValueError("Origin and destination stations must be different.")
        return self


class RouteCreate(RouteBase):
    pass


class RouteUpdate(RouteBase):
    pass


class RouteRead(RouteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
