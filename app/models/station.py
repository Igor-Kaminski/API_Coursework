from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = (UniqueConstraint("name", "city", name="uq_station_name_city"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    origin_routes = relationship(
        "Route",
        back_populates="origin_station",
        foreign_keys="Route.origin_station_id",
    )
    destination_routes = relationship(
        "Route",
        back_populates="destination_station",
        foreign_keys="Route.destination_station_id",
    )
    incidents = relationship("Incident", back_populates="station")
