from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
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

    origin_routes: Mapped[list["Route"]] = relationship(
        "Route",
        back_populates="origin_station",
        foreign_keys="Route.origin_station_id",
    )
    destination_routes: Mapped[list["Route"]] = relationship(
        "Route",
        back_populates="destination_station",
        foreign_keys="Route.destination_station_id",
    )
    incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        back_populates="station",
    )
