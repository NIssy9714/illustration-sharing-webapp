from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi_app.app.core.config import get_settings


def create_engine_from_settings():
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


engine = create_engine_from_settings()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

