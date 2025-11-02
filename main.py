from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from firebase_db import initialize_firebase
# REMOVED: voice_agent_journal router (PostgreSQL) - using Firebase voice_journal router instead
# from routers.voice_agent_journal import router as va_router  # ❌ PostgreSQL version
from routers.voice_agent import router as voice_agent_router
from routers.voice_journal import router as voice_journal_router  # ✅ Firebase version
from routers.priority_matrix import router as pm_router
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.daily_journal import router as daily_journal_router
from routers.moodboard import router as moodboard_router
from routers.stats import router as stats_router
from routers.wearable import router as wearable_router
from routers.reddit import router as reddit_router
from routers.wellness_analysis import router as wellness_router
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path
import os
import logging

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables - try .env.production first (for Cloud Run), then .env (for local dev)
env_path = Path(".env.production")
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"✅ Loaded .env.production from: {env_path.absolute()}")
else:
    load_dotenv()  # Fallback to .env for local development
    logger.info("✅ Loaded .env for local development")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - initialize Firebase (unified database).
    
    The application now uses Firebase Firestore exclusively for all features:
    - Wellness features, voice journals, stats, wearables, moodboards, chat
    - Reddit communities, priority matrix, authentication
    All data is stored in Firebase for real-time sync with Sahay ecosystem.
    """
    try:
        # Initialize Firebase (used for all features)
        initialize_firebase()
        logger.info("✅ Firebase initialized successfully")
        
        # Seed Reddit countries if they don't exist
        try:
            from seed_reddit_countries import seed_countries
            seed_countries()
            logger.info("✅ Countries seeded successfully")
        except Exception as e:
            logger.debug(f"Could not seed countries automatically: {str(e)}")
            logger.debug("You can run 'python seed_reddit_countries.py' manually if needed")
            
    except Exception as e:
        logger.error(f"❌ Firebase initialization failed: {e}")
        logger.warning("⚠️ Some features may not work without Firebase")
    
    yield
    
    # Cleanup on shutdown (if needed)
    logger.info("Application shutting down...")


app = FastAPI(lifespan=lifespan)

# CORS configuration - support both local development and production
# Get additional origins from environment variable (comma-separated)
allowed_origins = [
    "http://localhost:5173",  # Local frontend dev
    "http://127.0.0.1:5173",  # Local frontend dev (alternative)
    "http://localhost:3000",  # Alternative local port
    "http://127.0.0.1:3000",  # Alternative local port
]

# Add production origins from environment variable
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    production_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    allowed_origins.extend(production_origins)
    logger.info(f"✅ Production CORS origins added: {production_origins}")

logger.info(f"🔒 CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Allow cookies and credentials
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.get("/")
async def root():
    return {"message": "Sahay Backend API - Ready", "version": "1.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run and monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "sahay-backend",
        "database": "firebase",
    }


@app.get("/health-de1f4b3133627b2cacac9aad5ddfe07c")
async def get_health():
    """Legacy health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "google-hackathon-backend",
    }


# app.include_router(va_router)  # ❌ REMOVED: PostgreSQL version conflicts with Firebase
app.include_router(voice_agent_router)
app.include_router(voice_journal_router)  # ✅ Firebase version - FULL FIREBASE CONSISTENCY
app.include_router(pm_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(daily_journal_router)
app.include_router(moodboard_router)
app.include_router(stats_router)
app.include_router(wearable_router)
app.include_router(reddit_router)
app.include_router(wellness_router)
