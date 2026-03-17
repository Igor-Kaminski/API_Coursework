from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TransportMode


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "origin_station_id",
            "destination_station_id",
            name="uq_route_name_origin_destination",
        ),
        CheckConstraint("origin_station_id <> destination_station_id", name="ck_route_distinct_endpoints"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    origin_station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False, index=True)
    destination_station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id"), nullable=False, index=True
    )
    transport_mode: Mapped[TransportMode] = mapped_column(
        Enum(TransportMode, native_enum=False), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    origin_station = relationship("Station", back_populates="origin_routes", foreign_keys=[origin_station_id])
    destination_station = relationship(
        "Station",
        back_populates="destination_routes",
        foreign_keys=[destination_station_id],
    )
    incidents = relationship("Incident", back_populates="route")
