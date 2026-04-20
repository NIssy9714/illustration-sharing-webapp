from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Ensure models are registered for Alembic autogenerate
from fastapi_app.app import models as _models  # noqa: E402,F401

