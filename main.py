from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import create_db_and_tables
from routers.voice_agent_journal import router as va_router
from routers.priority_matrix import router as pm_router
from routers.auth import router as auth_router
from datetime import datetime, timezone


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


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
