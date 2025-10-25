from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os

from db import create_db_and_tables
from routers.voice_agent_journal import router as va_router
from routers.voice_agent import router as voice_agent_router
from routers.priority_matrix import router as pm_router
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.daily_journal import router as daily_journal_router
from routers.moodboard import router as moodboard_router
from routers.stats import router as stats_router
from routers.wearable import router as wearable_router
from datetime import datetime, timezone
from dotenv import load_dotenv
from hybrid_rag_manager import initialize_hybrid_rag_system
from transcript_manager import initialize_transcript_manager
from context_logger import initialize_context_logger

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    create_db_and_tables()
    
    # Initialize hybrid RAG system
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    if project_id:
        logger.info(f"Initializing hybrid RAG system for project: {project_id}")
        try:
            rag_success = await initialize_hybrid_rag_system(project_id)
            if rag_success:
                logger.info("Hybrid RAG system initialized successfully")
            else:
                logger.warning("Hybrid RAG system initialization failed - continuing without RAG")
        except Exception as e:
            logger.error(f"Error initializing hybrid RAG system: {e}")
    else:
        logger.warning("GOOGLE_CLOUD_PROJECT_ID not set - hybrid RAG system will not be available")
    
    # Initialize transcript manager
    logger.info("Initializing transcript manager...")
    try:
        initialize_transcript_manager(storage_type="database", transcripts_dir="transcripts")
        logger.info("Transcript manager initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing transcript manager: {e}")
    
    # Initialize context logger
    logger.info("Initializing context logger...")
    try:
        initialize_context_logger(logs_dir="logs", enable_database=True, enable_file=True)
        logger.info("Context logger initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing context logger: {e}")
    
    yield


app = FastAPI(lifespan=lifespan)

# CORS configuration - specify exact origins instead of wildcard when using credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local frontend dev
        "http://127.0.0.1:5173",  # Local frontend dev (alternative)
        "http://localhost:3000",  # Alternative local port
        "http://127.0.0.1:3000",  # Alternative local port
    ],
    allow_credentials=True,  # Allow cookies and credentials
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health-de1f4b3133627b2cacac9aad5ddfe07c")
async def get_health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "google-hackathon-backend",
    }


app.include_router(va_router)
app.include_router(voice_agent_router)
app.include_router(pm_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(daily_journal_router)
app.include_router(moodboard_router)
app.include_router(stats_router)
app.include_router(wearable_router)
