from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import Incident, Route, Station  # noqa: E402,F401
