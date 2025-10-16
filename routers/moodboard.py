from fastapi import APIRouter, Response, status
from sqlmodel import select
from db import SessionDep
from model import MoodboardData, MoodboardDataInput
from utils import TokenDep


router = APIRouter(tags=["Moodboard"])


@router.get("/moodboard")
async def get_moodboard_data(token_data: TokenDep, session: SessionDep):
    """Get moodboard data for the current user"""
    try:
        moodboard = session.exec(
            select(MoodboardData).where(MoodboardData.user_id == token_data.user_id)
        ).first()

        if not moodboard:
            # Return default data if none exists
            return {"study_mode": True, "data": {}}

        return {
            "id": str(moodboard.id),
            "study_mode": moodboard.study_mode,
            "data": moodboard.data or {},
        }
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.post("/moodboard", status_code=status.HTTP_201_CREATED)
async def create_moodboard_data(
    data: MoodboardDataInput, token_data: TokenDep, session: SessionDep
):
    """Create or update moodboard data for the current user"""
    try:
        # Check if moodboard data already exists
        existing = session.exec(
            select(MoodboardData).where(MoodboardData.user_id == token_data.user_id)
        ).first()

        if existing:
            # Update existing data
            existing.study_mode = data.study_mode
            if data.data is not None:
                existing.data = data.data

            session.add(existing)
            session.commit()
            session.refresh(existing)
            return Response(status_code=status.HTTP_200_OK)

        # Create new moodboard data
        new_moodboard = MoodboardData(
            user_id=token_data.user_id,
            study_mode=data.study_mode,
            data=data.data,
        )
        session.add(new_moodboard)
        session.commit()
        return Response(status_code=status.HTTP_201_CREATED)
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.patch("/moodboard")
async def update_moodboard_data(
    data: MoodboardDataInput, token_data: TokenDep, session: SessionDep
):
    """Update moodboard data for the current user"""
    try:
        moodboard = session.exec(
            select(MoodboardData).where(MoodboardData.user_id == token_data.user_id)
        ).first()

        if not moodboard:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Moodboard data not found. Please create data first.",
            )

        moodboard.study_mode = data.study_mode
        if data.data is not None:
            moodboard.data = data.data

        session.add(moodboard)
        session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )
