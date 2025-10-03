from fastapi import APIRouter, HTTPException, Response, status
from model import JounralSummaries
from db import SessionDep
from sqlmodel import select


router = APIRouter()


@router.post("/voice_agent_journal")
async def add_voice_agent_journal(data_received: JounralSummaries, session: SessionDep):
    try:
        new_row = JounralSummaries(
            id=data_received.id,
            user_name=data_received.user_name,
            study_mode=data_received.study_mode,
            data=data_received.data,
        )
        session.add(new_row)
        session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get("/voice_agent_journal")
async def get_voice_agent_journal(user_name: str, session: SessionDep):
    try:
        jounral_summaries = session.exec(
            select(JounralSummaries).where(JounralSummaries.user_name == user_name)
        ).all()

        if not jounral_summaries:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        else:
            return jounral_summaries
    except Exception as e:
        print(f"Exception: {e}")
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
