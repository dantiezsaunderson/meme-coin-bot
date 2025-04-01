"""
Database initialization and session management for the Meme Coin Signal Bot.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from ..config import DATABASE_URL
from .models import Base

# Create database engine
engine = create_engine(DATABASE_URL)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)

def get_session():
    """Get a database session."""
    session = Session()
    try:
        yield session
    finally:
        session.close()
