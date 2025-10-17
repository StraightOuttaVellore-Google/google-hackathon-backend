from fastapi import APIRouter, Response, status
from sqlmodel import select, func
from datetime import datetime, timezone
from db import SessionDep
from model import (
    SoundUsageLog,
    SoundUsageLogInput,
    EndSoundSessionInput,
    PomodoroSession,
    PomodoroSessionInput,
)
from utils import TokenDep


router = APIRouter(tags=["Stats"])


@router.post("/stats/sound/start", status_code=status.HTTP_201_CREATED)
async def start_sound_session(
    data: SoundUsageLogInput, token_data: TokenDep, session: SessionDep
):
    """Start a new sound usage session and return session ID"""
    try:
        new_session = SoundUsageLog(
            user_id=token_data.user_id,
            sound_type=data.sound_type,
            sound_name=data.sound_name,
        )
        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        return {
            "session_id": str(new_session.id),
            "started_at": new_session.started_at.isoformat()
            if new_session.started_at
            else None,
        }
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.patch("/stats/sound/{session_id}/end")
async def end_sound_session(session_id: str, token_data: TokenDep, session: SessionDep):
    """End a sound usage session and calculate duration"""
    try:
        # Parse session_id UUID
        import uuid

        session_uuid = uuid.UUID(session_id)

        # Find the session
        sound_session = session.exec(
            select(SoundUsageLog)
            .where(SoundUsageLog.id == session_uuid)
            .where(SoundUsageLog.user_id == token_data.user_id)
        ).first()

        if not sound_session:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Sound session not found",
            )

        # Update ended_at and calculate duration
        now = datetime.now(timezone.utc)
        sound_session.ended_at = now

        # Calculate duration in seconds
        if sound_session.started_at:
            duration = (now - sound_session.started_at).total_seconds()
            sound_session.duration_seconds = int(duration)

        session.add(sound_session)
        session.commit()

        return {
            "session_id": str(sound_session.id),
            "ended_at": sound_session.ended_at.isoformat(),
            "duration_seconds": sound_session.duration_seconds,
        }
    except ValueError as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid session ID format",
        )
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


# @TODO: We have to remove this from frontend because this is a useless
# function which was used as a placeholder earlier but now everything
# is accessible from their own endpoints
@router.get("/stats/monthly-overview/{year}/{month}")
async def get_monthly_overview(
    year: int, month: int, token_data: TokenDep, session: SessionDep
):
    """Get monthly overview statistics"""
    try:
        # Construct date range for the month
        from datetime import date

        if month == 12:
            start_date = date(year, month, 1)
            end_date = date(year + 1, 1, 1)
        else:
            start_date = date(year, month, 1)
            end_date = date(year, month + 1, 1)

        # Query sound sessions for the month
        sound_sessions = session.exec(
            select(SoundUsageLog)
            .where(SoundUsageLog.user_id == token_data.user_id)
            .where(SoundUsageLog.started_at >= start_date)
            .where(SoundUsageLog.started_at < end_date)
        ).all()

        # Calculate statistics
        total_duration_seconds = sum(
            s.duration_seconds or 0 for s in sound_sessions if s.duration_seconds
        )
        total_study_hours = total_duration_seconds / 3600

        study_days = set()
        for s in sound_sessions:
            if s.started_at:
                study_days.add(s.started_at.date())

        total_study_days = len(study_days)
        average_daily_hours = (
            total_study_hours / total_study_days if total_study_days > 0 else 0
        )

        # Calculate streak (placeholder - simplified)
        study_streak = min(total_study_days, 30)

        return {
            "study_overview": {
                "total_study_days": total_study_days,
                "total_study_hours": round(total_study_hours, 2),
                "average_daily_hours": round(average_daily_hours, 2),
                "study_streak": study_streak,
            },
            "emotional_trends": {
                "dominant_emotion": "FOCUSED",
                "emotion_distribution": {
                    "RELAXED": 2,
                    "BALANCED": 5,
                    "FOCUSED": 12,
                    "INTENSE": 3,
                    "OVERWHELMED": 1,
                    "BURNT_OUT": 0,
                },
                "emotional_score": 7.5,
            },
            "productivity_metrics": {
                "tasks_completed": 15,
                "tasks_created": 20,
                "completion_rate": 75,
            },
            "pomodoro_insights": {
                "total_pomodoros": 45,
                "average_work_time": 25,
                "focus_efficiency": 85,
            },
        }
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/stats/sound-preferences/{year}/{month}")
async def get_sound_preferences(
    year: int, month: int, token_data: TokenDep, session: SessionDep
):
    """Get sound usage preferences and analytics"""
    try:
        from datetime import date

        # Construct date range for the month
        if month == 12:
            start_date = date(year, month, 1)
            end_date = date(year + 1, 1, 1)
        else:
            start_date = date(year, month, 1)
            end_date = date(year, month + 1, 1)

        # Query sound sessions for the month
        sound_sessions = session.exec(
            select(SoundUsageLog)
            .where(SoundUsageLog.user_id == token_data.user_id)
            .where(SoundUsageLog.started_at >= start_date)
            .where(SoundUsageLog.started_at < end_date)
        ).all()

        # Analyze sound types
        ambient_count = sum(1 for s in sound_sessions if s.sound_type == "ambient")
        noise_count = sum(1 for s in sound_sessions if s.sound_type == "noise")
        total_count = len(sound_sessions)

        ambient_percentage = (
            (ambient_count / total_count * 100) if total_count > 0 else 50
        )

        # Find most used sound
        sound_counts = {}
        for s in sound_sessions:
            sound_counts[s.sound_name] = sound_counts.get(s.sound_name, 0) + 1

        most_used_sound = (
            max(sound_counts, key=sound_counts.get) if sound_counts else "FOREST"
        )

        return {
            "sound_usage": {
                "most_used_sound": most_used_sound.upper(),
                "noise_vs_ambient": {
                    "ambient_percentage": round(ambient_percentage, 1),
                    "noise_percentage": round(100 - ambient_percentage, 1),
                },
                "total_sessions": total_count,
            }
        }
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


# Pomodoro Tracking Endpoints
@router.post("/stats/pomodoro/start", status_code=status.HTTP_201_CREATED)
async def start_pomodoro_session(token_data: TokenDep, session: SessionDep):
    """Start a new pomodoro session and return session ID"""
    try:
        new_session = PomodoroSession(
            user_id=token_data.user_id,
            cycles_completed=0,
        )
        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        return {
            "session_id": str(new_session.id),
            "started_at": new_session.started_at.isoformat()
            if new_session.started_at
            else None,
        }
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.patch("/stats/pomodoro/{session_id}/end")
async def end_pomodoro_session(
    session_id: str,
    cycles_completed: int = 0,
    token_data: TokenDep = None,
    session: SessionDep = None,
):
    """End a pomodoro session and calculate duration"""
    try:
        import uuid

        session_uuid = uuid.UUID(session_id)

        # Find the session
        pomodoro_session = session.exec(
            select(PomodoroSession)
            .where(PomodoroSession.id == session_uuid)
            .where(PomodoroSession.user_id == token_data.user_id)
        ).first()

        if not pomodoro_session:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Pomodoro session not found",
            )

        # Update ended_at and calculate duration
        now = datetime.now(timezone.utc)
        pomodoro_session.ended_at = now
        pomodoro_session.cycles_completed = cycles_completed

        # Calculate duration in seconds
        if pomodoro_session.started_at:
            duration = (now - pomodoro_session.started_at).total_seconds()
            pomodoro_session.duration_seconds = int(duration)

        session.add(pomodoro_session)
        session.commit()

        return {
            "session_id": str(pomodoro_session.id),
            "ended_at": pomodoro_session.ended_at.isoformat(),
            "duration_seconds": pomodoro_session.duration_seconds,
            "cycles_completed": pomodoro_session.cycles_completed,
        }
    except ValueError as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid session ID format",
        )
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/stats/pomodoro-analytics/{year}/{month}")
async def get_pomodoro_analytics(
    year: int, month: int, token_data: TokenDep, session: SessionDep
):
    """Get pomodoro usage analytics for the month"""
    try:
        from datetime import date

        # Construct date range for the month
        if month == 12:
            start_date = date(year, month, 1)
            end_date = date(year + 1, 1, 1)
        else:
            start_date = date(year, month, 1)
            end_date = date(year, month + 1, 1)

        # Query pomodoro sessions for the month
        pomodoro_sessions = session.exec(
            select(PomodoroSession)
            .where(PomodoroSession.user_id == token_data.user_id)
            .where(PomodoroSession.started_at >= start_date)
            .where(PomodoroSession.started_at < end_date)
        ).all()

        # Calculate statistics
        total_duration_seconds = sum(
            s.duration_seconds or 0 for s in pomodoro_sessions if s.duration_seconds
        )
        total_study_hours = total_duration_seconds / 3600
        total_cycles = sum(s.cycles_completed or 0 for s in pomodoro_sessions)

        study_days = set()
        for s in pomodoro_sessions:
            if s.started_at:
                study_days.add(s.started_at.date())

        total_study_days = len(study_days)
        average_daily_hours = (
            total_study_hours / total_study_days if total_study_days > 0 else 0
        )
        average_cycles_per_session = (
            total_cycles / len(pomodoro_sessions) if len(pomodoro_sessions) > 0 else 0
        )

        return {
            "pomodoro_analytics": {
                "total_sessions": len(pomodoro_sessions),
                "total_study_days": total_study_days,
                "total_study_hours": round(total_study_hours, 2),
                "average_daily_hours": round(average_daily_hours, 2),
                "total_cycles_completed": total_cycles,
                "average_cycles_per_session": round(average_cycles_per_session, 2),
            }
        }
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )
