from fastapi import APIRouter, Response, status
from sqlmodel import select
from db import SessionDep
from model import SoundPreferences, SoundPreferencesInput
from utils import TokenDep


router = APIRouter(tags=["Sound"])


@router.get("/sound")
async def get_sound_preferences(token_data: TokenDep, session: SessionDep):
    """Get sound preferences for the current user"""
    try:
        preferences = session.exec(
            select(SoundPreferences).where(
                SoundPreferences.user_id == token_data.user_id
            )
        ).first()

        if not preferences:
            # Return default preferences if none exist
            return {"selected_sound": "none", "volume": 0.5, "is_playing": False}

        return {
            "id": str(preferences.id),
            "selected_sound": preferences.selected_sound,
            "volume": preferences.volume,
            "is_playing": preferences.is_playing,
        }
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.post("/sound", status_code=status.HTTP_201_CREATED)
async def create_sound_preferences(
    data: SoundPreferencesInput, token_data: TokenDep, session: SessionDep
):
    """Create or update sound preferences for the current user"""
    try:
        # Check if preferences already exist
        existing = session.exec(
            select(SoundPreferences).where(
                SoundPreferences.user_id == token_data.user_id
            )
        ).first()

        if existing:
            # Update existing preferences
            if data.selected_sound is not None:
                existing.selected_sound = data.selected_sound
            if data.volume is not None:
                existing.volume = data.volume
            if data.is_playing is not None:
                existing.is_playing = data.is_playing

            session.add(existing)
            session.commit()
            session.refresh(existing)
            return Response(status_code=status.HTTP_200_OK)

        # Create new preferences
        new_preferences = SoundPreferences(
            user_id=token_data.user_id,
            selected_sound=data.selected_sound or "none",
            volume=data.volume if data.volume is not None else 0.5,
            is_playing=data.is_playing if data.is_playing is not None else False,
        )
        session.add(new_preferences)
        session.commit()
        return Response(status_code=status.HTTP_201_CREATED)
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.patch("/sound")
async def update_sound_preferences(
    data: SoundPreferencesInput, token_data: TokenDep, session: SessionDep
):
    """Update sound preferences for the current user"""
    try:
        preferences = session.exec(
            select(SoundPreferences).where(
                SoundPreferences.user_id == token_data.user_id
            )
        ).first()

        if not preferences:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Preferences not found. Please create preferences first.",
            )

        if data.selected_sound is not None:
            preferences.selected_sound = data.selected_sound
        if data.volume is not None:
            preferences.volume = data.volume
        if data.is_playing is not None:
            preferences.is_playing = data.is_playing

        session.add(preferences)
        session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )
