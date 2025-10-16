from fastapi import APIRouter, Response, status
from sqlmodel import select
from db import SessionDep
from model import PomodoroSettings, PomodoroSettingsInput
from utils import TokenDep


router = APIRouter(tags=["Pomodoro"])


@router.get("/pomodoro")
async def get_pomodoro_settings(token_data: TokenDep, session: SessionDep):
    """Get pomodoro settings for the current user"""
    try:
        settings = session.exec(
            select(PomodoroSettings).where(
                PomodoroSettings.user_id == token_data.user_id
            )
        ).first()

        if not settings:
            # Return default settings if none exist
            return {
                "work_duration": 25,
                "short_break": 5,
                "long_break": 15,
                "sessions_before_long_break": 4,
            }

        return {
            "id": str(settings.id),
            "work_duration": settings.work_duration,
            "short_break": settings.short_break,
            "long_break": settings.long_break,
            "sessions_before_long_break": settings.sessions_before_long_break,
        }
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.post("/pomodoro", status_code=status.HTTP_201_CREATED)
async def create_pomodoro_settings(
    data: PomodoroSettingsInput, token_data: TokenDep, session: SessionDep
):
    """Create or update pomodoro settings for the current user"""
    try:
        # Check if settings already exist
        existing = session.exec(
            select(PomodoroSettings).where(
                PomodoroSettings.user_id == token_data.user_id
            )
        ).first()

        if existing:
            # Update existing settings
            if data.work_duration is not None:
                existing.work_duration = data.work_duration
            if data.short_break is not None:
                existing.short_break = data.short_break
            if data.long_break is not None:
                existing.long_break = data.long_break
            if data.sessions_before_long_break is not None:
                existing.sessions_before_long_break = data.sessions_before_long_break

            session.add(existing)
            session.commit()
            session.refresh(existing)
            return Response(status_code=status.HTTP_200_OK)

        # Create new settings
        new_settings = PomodoroSettings(
            user_id=token_data.user_id,
            work_duration=data.work_duration or 25,
            short_break=data.short_break or 5,
            long_break=data.long_break or 15,
            sessions_before_long_break=data.sessions_before_long_break or 4,
        )
        session.add(new_settings)
        session.commit()
        return Response(status_code=status.HTTP_201_CREATED)
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.patch("/pomodoro")
async def update_pomodoro_settings(
    data: PomodoroSettingsInput, token_data: TokenDep, session: SessionDep
):
    """Update pomodoro settings for the current user"""
    try:
        settings = session.exec(
            select(PomodoroSettings).where(
                PomodoroSettings.user_id == token_data.user_id
            )
        ).first()

        if not settings:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Settings not found. Please create settings first.",
            )

        if data.work_duration is not None:
            settings.work_duration = data.work_duration
        if data.short_break is not None:
            settings.short_break = data.short_break
        if data.long_break is not None:
            settings.long_break = data.long_break
        if data.sessions_before_long_break is not None:
            settings.sessions_before_long_break = data.sessions_before_long_break

        session.add(settings)
        session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )
