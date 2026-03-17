from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import IncidentStatus, IncidentType, Severity


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("delay_minutes IS NULL OR delay_minutes >= 0", name="ck_incident_delay_non_negative"),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= occurred_at",
            name="ck_incident_resolved_after_occurred",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False, index=True)
    station_id: Mapped[int | None] = mapped_column(ForeignKey("stations.id"), nullable=True, index=True)
    incident_type: Mapped[IncidentType] = mapped_column(
        Enum(IncidentType, native_enum=False), nullable=False, index=True
    )
    severity: Mapped[Severity] = mapped_column(Enum(Severity, native_enum=False), nullable=False, index=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False),
        nullable=False,
        index=True,
        default=IncidentStatus.open,
        server_default=text("'open'"),
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    delay_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    route = relationship("Route", back_populates="incidents")
    station = relationship("Station", back_populates="incidents")
