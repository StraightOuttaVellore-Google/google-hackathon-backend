"""
Stats Router - Firebase Version
All stats tracking now uses Firebase Firestore
"""

from fastapi import APIRouter, status, HTTPException
from datetime import datetime, timezone
from pydantic import BaseModel
from firebase_db import get_firestore
import uuid

from utils import TokenDep


# Pydantic models for input validation
class SoundUsageLogInput(BaseModel):
    sound_type: str
    sound_name: str

class PomodoroSessionInput(BaseModel):
    pass


router = APIRouter(tags=["Stats"])


# ============================================================================
# SOUND SESSION ENDPOINTS
# ============================================================================

@router.post("/stats/sound/start", status_code=status.HTTP_201_CREATED)
async def start_sound_session(
    data: SoundUsageLogInput, 
    token_data: TokenDep
):
    """Start a new sound usage session in Firebase Firestore"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Create session document in Firestore
        session_data = {
            "user_id": user_id,
            "sound_type": data.sound_type,
            "sound_name": data.sound_name,
            "started_at": now,
            "ended_at": None,
            "duration_seconds": None,
            "created_at": now,
        }
        
        db.collection('soundUsageLogs').document(session_id).set(session_data)
        
        return {
            "session_id": session_id,
            "started_at": now.isoformat(),
        }
    except Exception as e:
        print(f"❌ Error starting sound session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sound session: {str(e)}"
        )


@router.patch("/stats/sound/{session_id}/end")
async def end_sound_session(
    session_id: str, 
    token_data: TokenDep
):
    """End a sound usage session in Firebase Firestore"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Get session document
        session_ref = db.collection('soundUsageLogs').document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sound session not found"
            )
        
        session_data = session_doc.to_dict()
        
        # Verify user ownership
        if session_data.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to end this session"
            )
        
        # Update session with end time
        now = datetime.now(timezone.utc)
        started_at = session_data.get("started_at")
        
        # Calculate duration
        duration_seconds = None
        if started_at:
            if hasattr(started_at, 'timestamp'):
                duration = (now - started_at).total_seconds()
            elif hasattr(started_at, 'replace'):
                duration = (now - started_at.replace(tzinfo=timezone.utc)).total_seconds()
            else:
                duration = 0
            duration_seconds = int(duration)
        
        session_ref.update({
            "ended_at": now,
            "duration_seconds": duration_seconds,
            "updated_at": now,
        })
        
        return {
            "session_id": session_id,
            "ended_at": now.isoformat(),
            "duration_seconds": duration_seconds,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error ending sound session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end sound session: {str(e)}"
        )


@router.get("/stats/sound-preferences/{year}/{month}")
async def get_sound_preferences(
    year: int, 
    month: int, 
    token_data: TokenDep
):
    """Get sound usage preferences for the month from Firebase"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Construct date range for the month (Firestore needs datetime, not date)
        if month == 12:
            start_datetime = datetime(year, month, 1, tzinfo=timezone.utc)
            end_datetime = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            start_datetime = datetime(year, month, 1, tzinfo=timezone.utc)
            end_datetime = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        # Query sound sessions - ONLY filter by user_id to avoid index requirement
        sessions_ref = db.collection('soundUsageLogs')
        query = sessions_ref.where('user_id', '==', user_id)
        
        all_sessions = list(query.stream())
        
        # Filter by date in Python
        sound_sessions = []
        for doc in all_sessions:
            data = doc.to_dict()
            started_at = data.get('started_at')
            if started_at:
                # Handle different timestamp types
                if hasattr(started_at, 'replace'):
                    session_datetime = started_at.replace(tzinfo=timezone.utc)
                elif hasattr(started_at, 'timestamp'):
                    session_datetime = started_at
                else:
                    continue
                
                if start_datetime <= session_datetime < end_datetime:
                    sound_sessions.append(doc)
        
        # Analyze sound types
        ambient_count = sum(1 for doc in sound_sessions if doc.to_dict().get('sound_type') == "ambient")
        noise_count = sum(1 for doc in sound_sessions if doc.to_dict().get('sound_type') == "noise")
        total_count = len(sound_sessions)
        
        ambient_percentage = (ambient_count / total_count * 100) if total_count > 0 else 50
        
        # Find most used sound
        sound_counts = {}
        for doc in sound_sessions:
            sound_name = doc.to_dict().get('sound_name', 'FOREST')
            sound_counts[sound_name] = sound_counts.get(sound_name, 0) + 1
        
        most_used_sound = max(sound_counts, key=sound_counts.get) if sound_counts else "FOREST"
        
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
        print(f"❌ Error getting sound preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sound preferences: {str(e)}"
        )


# ============================================================================
# POMODORO SESSION ENDPOINTS
# ============================================================================

@router.post("/stats/pomodoro/start", status_code=status.HTTP_201_CREATED)
async def start_pomodoro_session(token_data: TokenDep):
    """Start a new pomodoro session in Firebase Firestore"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Create session document in Firestore
        session_data = {
            "user_id": user_id,
            "cycles_completed": 0,
            "started_at": now,
            "ended_at": None,
            "duration_seconds": None,
            "created_at": now,
        }
        
        db.collection('pomodoroSessions').document(session_id).set(session_data)
        
        return {
            "session_id": session_id,
            "started_at": now.isoformat(),
        }
    except Exception as e:
        print(f"❌ Error starting pomodoro session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start pomodoro session: {str(e)}"
        )


@router.patch("/stats/pomodoro/{session_id}/end")
async def end_pomodoro_session(
    session_id: str,
    cycles_completed: int = 0,
    token_data: TokenDep = None,
):
    """End a pomodoro session in Firebase Firestore"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Get session document
        session_ref = db.collection('pomodoroSessions').document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pomodoro session not found"
            )
        
        session_data = session_doc.to_dict()
        
        # Verify user ownership
        if session_data.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to end this session"
            )
        
        # Update session with end time
        now = datetime.now(timezone.utc)
        started_at = session_data.get("started_at")
        
        # Calculate duration
        duration_seconds = None
        if started_at:
            if hasattr(started_at, 'timestamp'):
                duration = (now - started_at).total_seconds()
            elif hasattr(started_at, 'replace'):
                duration = (now - started_at.replace(tzinfo=timezone.utc)).total_seconds()
            else:
                duration = 0
            duration_seconds = int(duration)
        
        session_ref.update({
            "ended_at": now,
            "duration_seconds": duration_seconds,
            "cycles_completed": cycles_completed,
            "updated_at": now,
        })
        
        return {
            "session_id": session_id,
            "ended_at": now.isoformat(),
            "duration_seconds": duration_seconds,
            "cycles_completed": cycles_completed,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error ending pomodoro session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end pomodoro session: {str(e)}"
        )


@router.get("/stats/pomodoro-analytics/{year}/{month}")
async def get_pomodoro_analytics(
    year: int, 
    month: int, 
    token_data: TokenDep
):
    """Get pomodoro usage analytics for the month from Firebase"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Construct date range for the month (Firestore needs datetime, not date)
        if month == 12:
            start_datetime = datetime(year, month, 1, tzinfo=timezone.utc)
            end_datetime = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            start_datetime = datetime(year, month, 1, tzinfo=timezone.utc)
            end_datetime = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        # Query pomodoro sessions - ONLY filter by user_id to avoid index requirement
        sessions_ref = db.collection('pomodoroSessions')
        query = sessions_ref.where('user_id', '==', user_id)
        
        all_sessions = list(query.stream())
        
        # Filter by date in Python
        pomodoro_sessions = []
        for doc in all_sessions:
            data = doc.to_dict()
            started_at = data.get('started_at')
            if started_at:
                # Handle different timestamp types
                if hasattr(started_at, 'replace'):
                    session_datetime = started_at.replace(tzinfo=timezone.utc)
                elif hasattr(started_at, 'timestamp'):
                    session_datetime = started_at
                else:
                    continue
                
                if start_datetime <= session_datetime < end_datetime:
                    pomodoro_sessions.append(doc)
        
        # Calculate statistics
        total_duration_seconds = 0
        total_cycles = 0
        study_days = set()
        
        for doc in pomodoro_sessions:
            data = doc.to_dict()
            duration = data.get('duration_seconds') or 0
            total_duration_seconds += duration
            total_cycles += data.get('cycles_completed', 0)
            
            started_at = data.get('started_at')
            if started_at:
                if hasattr(started_at, 'date'):
                    study_days.add(started_at.date())
                elif hasattr(started_at, 'replace'):
                    study_days.add(started_at.replace(tzinfo=timezone.utc).date())
        
        total_study_hours = total_duration_seconds / 3600
        total_study_days = len(study_days)
        average_daily_hours = (total_study_hours / total_study_days) if total_study_days > 0 else 0
        average_cycles_per_session = (total_cycles / len(pomodoro_sessions)) if len(pomodoro_sessions) > 0 else 0
        
        return {
            "pomodoro_analytics": {
                "total_study_hours": round(total_study_hours, 2),
                "total_study_days": total_study_days,
                "average_daily_hours": round(average_daily_hours, 2),
                "total_cycles": total_cycles,
                "average_cycles_per_session": round(average_cycles_per_session, 1),
                "total_sessions": len(pomodoro_sessions),
            }
        }
    except Exception as e:
        print(f"❌ Error getting pomodoro analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pomodoro analytics: {str(e)}"
        )


# ============================================================================
# MONTHLY OVERVIEW (Deprecated - use specific endpoints instead)
# ============================================================================

@router.get("/stats/monthly-overview/{year}/{month}")
async def get_monthly_overview(
    year: int, 
    month: int, 
    token_data: TokenDep
):
    """
    Legacy endpoint - use specific endpoints instead
    Returns basic stats for backwards compatibility
    """
    try:
        # Return basic mock data for compatibility
        return {
            "message": "This endpoint is deprecated. Use specific endpoints: /stats/pomodoro-analytics and /stats/sound-preferences",
            "study_hours": 0,
            "pomodoro_sessions": 0,
            "sound_sessions": 0,
        }
    except Exception as e:
        print(f"❌ Error in monthly overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monthly overview: {str(e)}"
        )
