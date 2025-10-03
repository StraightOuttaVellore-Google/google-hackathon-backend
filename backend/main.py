from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import create_db_and_tables
from voice_agent_journal import router as va_router
from priority_matrix import router as pm_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(va_router)
app.include_router(pm_router)
