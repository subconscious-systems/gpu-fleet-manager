from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
import logging

from src.config import get_settings
from src.config.utils import get_database_url

# Configure logger
logger = logging.getLogger(__name__)

# Create SQLAlchemy base
Base = declarative_base()

# Get database URL from configuration
DATABASE_URL = get_database_url()
logger.info(f"Initializing database connection to {DATABASE_URL.replace('://', '://*:*@')}")

# Create engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """
    Dependency for getting database session
    
    Returns:
        SQLAlchemy Session to use for database operations
        
    Note:
        Uses context manager to ensure session is closed after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
