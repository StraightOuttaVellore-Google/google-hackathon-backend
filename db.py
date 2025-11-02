"""
Database module - PostgreSQL (optional, only if configured)
Since migration to Firebase, this is kept for backward compatibility only.
Most routers now use Firebase via firebase_db.py
"""
from fastapi import Depends
from typing import Annotated, Optional
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables - try .env.production first (for Cloud Run), then .env (for local dev)
env_path = Path(".env.production")
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback to .env for local development
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Helper function to check if a value is valid (not None and not the string "None")
def is_valid_db_value(value):
    """Check if database config value is valid (not None/empty/string 'None')"""
    if not value:
        return False
    if isinstance(value, str) and value.strip().lower() == "none":
        return False
    return True

# Initialize engine as None (lazy loading)
engine = None
SessionLocal = None
SessionDep = None

# Only create PostgreSQL engine if all config is present and valid
if all([
    is_valid_db_value(DB_USER),
    is_valid_db_value(DB_PASSWORD),
    is_valid_db_value(DB_HOST),
    is_valid_db_value(DB_PORT),
    is_valid_db_value(DB_NAME)
]):
    try:
        from sqlmodel import Session, SQLModel, create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Construct the PostgreSQL connection URL
        postgresql_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(postgresql_url)
        
        # Create SessionLocal for background tasks
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        def get_session():
            with Session(engine) as session:
                yield session
        
        SessionDep = Annotated[Session, Depends(get_session)]
        
    except Exception as e:
        # If PostgreSQL dependencies fail, engine stays None
        print(f"⚠️ PostgreSQL not configured or unavailable: {e}")
        print("✅ Using Firebase instead (recommended)")
        # Create a dummy SessionDep for type hints (but it won't be used)
        from typing import Any
        SessionDep = Optional[Any]  # Type placeholder, won't actually be used
else:
    # PostgreSQL not configured - using Firebase
    print("ℹ️ PostgreSQL not configured - using Firebase (recommended for production)")
    
    # Create a dummy SessionDep for type hints (but it won't be used)
    from typing import Any
    SessionDep = Optional[Any]  # Type placeholder, won't actually be used


def create_db_and_tables():
    """Create database tables (only if PostgreSQL is configured)"""
    if engine is not None:
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine)
    else:
        print("ℹ️ PostgreSQL not configured - skipping table creation (using Firebase)")
