from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""


from app.models import Incident, JourneyRecord, Route, Station

__all__ = ["Base", "Incident", "JourneyRecord", "Route", "Station"]
