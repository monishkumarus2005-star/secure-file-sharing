"""
Database Configuration Module
Handles PostgreSQL connection and SQLAlchemy setup
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,  # Maximum number of connections to keep in pool
    max_overflow=20,  # Maximum overflow connections
    echo=settings.DEBUG  # Log SQL queries in debug mode
)

# SessionLocal factory for creating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for declarative models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI routes
    Provides a database session and ensures proper cleanup
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables
    Creates all tables defined in models
    """
    from app import models  # Import models to register them
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import logging
        logging.warning(f"Database initialization metadata crash bypassed: {e}")
