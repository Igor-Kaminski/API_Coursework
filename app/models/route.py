from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint(
            "origin_station_id",
            "destination_station_id",
            "name",
            name="uq_routes_origin_destination_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    origin_station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id"),
        nullable=False,
    )
    destination_station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    origin_station: Mapped["Station"] = relationship(
        "Station",
        back_populates="origin_routes",
        foreign_keys=[origin_station_id],
    )
    destination_station: Mapped["Station"] = relationship(
        "Station",
        back_populates="destination_routes",
        foreign_keys=[destination_station_id],
    )
    journey_records: Mapped[list["JourneyRecord"]] = relationship(
        "JourneyRecord",
        back_populates="route",
        cascade="all, delete-orphan",
    )
    incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        back_populates="route",
    )
