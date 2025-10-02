from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, status
from model import JounralSummaries
from db import SessionDep, create_db_and_tables
import voice_agent_journal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(voice_agent_journal.router)
