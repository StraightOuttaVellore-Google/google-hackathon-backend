from typing import List
from fastapi import APIRouter, HTTPException, Response, status
from model import JournalSummaries, JournalSummariesInput
from db import SessionDep
from sqlmodel import select

from utils import TokenDep

router = APIRouter(tags=["VoiceAgent"])


@router.post("/voice_agent_journal", response_model=JournalSummaries)
async def add_voice_agent_journal(
    data_received: JournalSummariesInput, token_data: TokenDep, session: SessionDep
):
    try:
        new_row = JournalSummaries(
            user_id=token_data.user_id,
            study_mode=data_received.study_mode,
            data=data_received.data,
        )
        session.add(new_row)
        session.commit()
        session.refresh(new_row)
        return new_row
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error:\n{e}",
        )


@router.get("/voice_agent_journal", response_model=List[JournalSummaries])
async def get_voice_agent_journal(token_data: TokenDep, session: SessionDep):
    try:
        jounral_summaries = session.exec(
            select(JournalSummaries)
            .where(JournalSummaries.user_id == token_data.user_id)
            .order_by(JournalSummaries.created_at)
        ).all()

        if not jounral_summaries:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        else:
            return jounral_summaries
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )
