from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import create_db_and_tables
from routers.voice_agent_journal import router as va_router
from routers.priority_matrix import router as pm_router
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.pomodoro import router as pomodoro_router
from routers.sound import router as sound_router
from routers.daily_journal import router as daily_journal_router
from routers.moodboard import router as moodboard_router
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(pm_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(pomodoro_router)
app.include_router(sound_router)
app.include_router(daily_journal_router)
app.include_router(moodboard_router)
