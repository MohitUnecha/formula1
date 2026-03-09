"""Database connection and session management"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config import settings

# Create engine with backend-specific settings
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        echo=False,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database schema"""
    from models import (
        Event, Session, Driver, DriverSession, Lap, PitStop,
        Weather, RaceControl, Prediction, FeatureStore, ShapExplanation
    )
    Base.metadata.create_all(bind=engine)
