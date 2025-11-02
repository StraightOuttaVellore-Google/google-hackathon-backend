"""
Voice Journal Router - Firebase Version

Handles voice journal session completion, wellness analysis triggering,
and analysis result polling using Firestore for real-time sync.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import uuid
import json
import sys
from pathlib import Path
import asyncio
from datetime import datetime
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# Add agents directory to path
agents_path = Path(__file__).parent.parent / "agents"
sys.path.insert(0, str(agents_path))

from model import (
    VoiceJournalSessionInput,
    VoiceJournalAnalysisResult,
    WellnessMode,
)
from firebase_db import get_firestore
from utils import get_current_user

# Import orchestrator
try:
    from agents.orchestrator import run_wellness_analysis
except ImportError as e:
    print(f"Warning: Could not import orchestrator: {e}")
    run_wellness_analysis = None

router = APIRouter(prefix="/voice_journal", tags=["voice_journal"])


@router.post("/complete")
async def complete_voice_journal_session(
    session_data: VoiceJournalSessionInput,
    current_user = Depends(get_current_user),
):
    """
    Complete a voice journal session and trigger wellness analysis
    
    Flow:
    1. Save voice journal session to Firestore
    2. Start wellness analysis in background
    3. Return session_id for polling
    4. Frontend can use real-time listener instead of polling!
    """
    try:
        print(f"📥 Voice journal complete endpoint called")
        print(f"   Mode: {session_data.mode}")
        print(f"   Mode value: {session_data.mode.value}")
        print(f"   Transcript length: {len(session_data.transcript)}")
        print(f"   Duration: {session_data.duration_seconds}")
        print(f"👤 User: {current_user.user_id} ({current_user.username})")
        
        db = get_firestore()
        print(f"✅ Firestore client obtained")
        
        user_id = str(current_user.user_id)
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        print(f"📝 Generated session ID: {session_id}")
        
        # Create voice journal session document
        session_doc = {
            "user_id": user_id,
            "mode": session_data.mode.value,
            "transcript": session_data.transcript,
            "duration_seconds": session_data.duration_seconds,
            "analysis_completed": False,
            "analysis_data": None,
            "created_at": SERVER_TIMESTAMP,
        }
        
        print(f"💾 Saving to Firestore collection: voiceJournalSessions")
        # Save to Firestore
        sessions_ref = db.collection('voiceJournalSessions')
        sessions_ref.document(session_id).set(session_doc)
        print(f"✅ Successfully saved session to Firestore")
        
        # Start analysis in background (non-blocking)
        print(f"🚀 Starting background analysis task...")
        asyncio.create_task(
            process_analysis_async(
                session_id=session_id,
                transcript=session_data.transcript,
                mode=session_data.mode,
                user_id=user_id
            )
        )
        print(f"✅ Background analysis task started")
        
        response_data = {
            "message": "Voice journal session saved. Analysis started.",
            "session_id": session_id,
            "mode": session_data.mode.value,
            "analysis_status": "processing",
        }
        print(f"📤 Returning response: {response_data}")
        
        return response_data
        
    except Exception as e:
        print(f"❌ ERROR in complete_voice_journal_session: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save voice journal session: {str(e)}"
        )


async def process_analysis_async(session_id: str, transcript: str, mode: WellnessMode, user_id: str):
    """
    Process wellness analysis in background
    Updates Firestore when complete (real-time sync!)
    """
    print(f"🧠 [ANALYSIS] Starting analysis for session {session_id}")
    print(f"   Mode: {mode}")
    print(f"   User ID: {user_id}")
    print(f"   Transcript length: {len(transcript)}")
    
    db = get_firestore()
    session_ref = db.collection('voiceJournalSessions').document(session_id)
    
    try:
        if run_wellness_analysis is None:
            raise Exception("Wellness analysis service not available")
        
        print(f"🔄 [ANALYSIS] Running wellness analysis agents...")
        # Run analysis - mode is already WellnessMode enum
        analysis_result = await run_wellness_analysis(
            transcript=transcript,
            mode=mode.value if hasattr(mode, 'value') else mode,  # Ensure string value
            user_id=user_id,
            session_id=session_id
        )
        
        print(f"✅ [ANALYSIS] Analysis completed successfully")
        print(f"   Result type: {type(analysis_result)}")
        
        # Update Firestore document with results (real-time sync!)
        # Handle both dict and Pydantic model responses
        if isinstance(analysis_result, dict):
            analysis_dict = analysis_result
        elif hasattr(analysis_result, 'model_dump'):
            analysis_dict = analysis_result.model_dump()
        elif hasattr(analysis_result, 'dict'):
            analysis_dict = analysis_result.dict()
        else:
            # Fallback: try to convert to dict
            analysis_dict = dict(analysis_result) if analysis_result else {}
        
        print(f"📊 [ANALYSIS] Analysis has transcript_summary: {'transcript_summary' in analysis_dict}")
        print(f"📊 [ANALYSIS] Analysis has stats_recommendations: {'stats_recommendations' in analysis_dict}")
        
        update_data = {
            "analysis_data": analysis_dict,
            "analysis_completed": True,
            "updated_at": SERVER_TIMESTAMP,
        }
        
        print(f"💾 [ANALYSIS] Updating Firestore...")
        session_ref.update(update_data)
        
        print(f"✅✅✅ Analysis completed and saved for session {session_id}")
        
    except Exception as e:
        print(f"❌ [ANALYSIS] Analysis failed for session {session_id}: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Update session to show failure
        try:
            error_data = {
                "analysis_data": {
                    "error": str(e),
                    "status": "failed"
                },
                "analysis_completed": False,
                "updated_at": SERVER_TIMESTAMP,
            }
            session_ref.update(error_data)
            print(f"📝 [ANALYSIS] Updated session with error status")
        except Exception as update_error:
            print(f"❌ [ANALYSIS] Failed to update session with error: {update_error}")


@router.get("/analysis/{session_id}")
async def get_session_analysis(
    session_id: str,
    current_user = Depends(get_current_user),
):
    """
    Get wellness analysis results for a session
    
    Note: For real-time updates, use Firestore listeners in frontend
    instead of polling this endpoint!
    
    Returns:
    - status: "processing" | "completed" | "failed"
    - analysis: Full analysis object (when completed)
    - transcript: Original transcript
    - mode: Voice journal mode
    """
    try:
        db = get_firestore()
        user_id = str(current_user.user_id)
        
        # Get session from Firestore
        session_ref = db.collection('voiceJournalSessions').document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session_data = session_doc.to_dict()
        
        # Verify ownership
        if session_data.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
        
        # Check analysis status
        analysis_completed = session_data.get("analysis_completed", False)
        analysis_data = session_data.get("analysis_data")
        
        if analysis_completed and analysis_data:
            # Check if it's an error
            if isinstance(analysis_data, dict) and "error" in analysis_data:
                return {
                    "status": "failed",
                    "message": analysis_data.get("error", "Unknown error"),
                    "transcript": session_data.get("transcript"),
                    "mode": session_data.get("mode"),
                }
            
            # Success
            return {
                "status": "completed",
                "analysis": analysis_data,
                "transcript": session_data.get("transcript"),
                "mode": session_data.get("mode"),
            }
        else:
            # Still processing
            return {
                "status": "processing",
                "message": "Analysis in progress. Please wait...",
                "transcript": session_data.get("transcript"),
                "mode": session_data.get("mode"),
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session: {str(e)}"
        )


@router.get("/sessions")
async def get_user_sessions(
    limit: int = 10,
    current_user = Depends(get_current_user),
):
    """
    Get user's voice journal sessions
    
    Returns last N sessions with their analysis status
    
    Note: Use Firestore queries with real-time listeners in frontend
    for live updates!
    """
    try:
        db = get_firestore()
        user_id = str(current_user.user_id)
        
        # Query Firestore
        sessions_ref = db.collection('voiceJournalSessions')
        query = sessions_ref.where('user_id', '==', user_id)\
                           .order_by('created_at', direction='DESCENDING')\
                           .limit(limit)
        
        sessions_docs = query.stream()
        
        sessions = []
        for doc in sessions_docs:
            data = doc.to_dict()
            created_at = data.get("created_at")
            if hasattr(created_at, 'isoformat'):
                created_at_str = created_at.isoformat()
            elif isinstance(created_at, datetime):
                created_at_str = created_at.isoformat()
            else:
                created_at_str = None
            
            sessions.append({
                "id": doc.id,
                "mode": data.get("mode"),
                "duration_seconds": data.get("duration_seconds"),
                "analysis_completed": data.get("analysis_completed", False),
                "created_at": created_at_str,
                "has_analysis": data.get("analysis_data") is not None and data.get("analysis_completed", False),
            })
        
        return {"sessions": sessions}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sessions: {str(e)}"
        )


@router.get("/summaries")
async def get_voice_journal_summaries(
    limit: int = 20,
    current_user = Depends(get_current_user),
):
    """
    Get user's voice journal session summaries with AI analysis
    
    Returns summaries sorted by most recent first, including:
    - Session ID, date, duration
    - AI-generated summary from transcript_summary
    - Emotions and focus areas
    - Key insights
    
    Used for the right-hand summary panel in voice agent UI
    """
    try:
        db = get_firestore()
        user_id = str(current_user.user_id)
        
        # Query Firestore - ONLY filter by user_id (no orderBy to avoid index requirement)
        sessions_ref = db.collection('voiceJournalSessions')
        query = sessions_ref.where('user_id', '==', user_id)
        
        sessions_docs = query.stream()
        
        # Collect all sessions with timestamps for sorting
        sessions_with_timestamps = []
        
        for doc in sessions_docs:
            try:
                data = doc.to_dict()
                
                # Skip if analysis not completed
                if not data.get("analysis_completed", False):
                    continue
                
                analysis_data = data.get("analysis_data", {})
                if not analysis_data or not isinstance(analysis_data, dict):
                    continue
                
                transcript_summary = analysis_data.get("transcript_summary", {})
                if not transcript_summary:
                    continue
                
                # Parse created_at timestamp for sorting
                created_at = data.get("created_at")
                if hasattr(created_at, 'isoformat'):
                    created_at_dt = created_at
                    timestamp_for_sort = created_at.timestamp()
                elif isinstance(created_at, str):
                    try:
                        created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        timestamp_for_sort = created_at_dt.timestamp()
                    except:
                        created_at_dt = datetime.utcnow()
                        timestamp_for_sort = created_at_dt.timestamp()
                else:
                    created_at_dt = datetime.utcnow()
                    timestamp_for_sort = created_at_dt.timestamp()
                
                # Format duration
                duration_seconds = data.get("duration_seconds", 0)
                duration_str = f"{duration_seconds // 60} min" if duration_seconds >= 60 else f"{duration_seconds} sec"
                
                # Build summary object
                summary = {
                    "id": doc.id,
                    "session_id": doc.id,
                    "date": created_at_dt.strftime("%Y-%m-%d"),
                    "time": created_at_dt.strftime("%H:%M"),
                    "duration": duration_str,
                    "mode": data.get("mode", "wellness"),
                    "title": transcript_summary.get("summary", "Voice Journal Session")[:50] + "...",
                    "summary": transcript_summary.get("summary", ""),
                    "emotions": transcript_summary.get("emotions", []),
                    "focus_areas": transcript_summary.get("focus_areas", []),
                    "stress_level": transcript_summary.get("stress_level"),
                    "academic_concerns": transcript_summary.get("academic_concerns", []),
                    "key_insights": transcript_summary.get("key_insights", []),
                    "_timestamp": timestamp_for_sort  # For sorting
                }
                
                sessions_with_timestamps.append(summary)
                    
            except Exception as doc_error:
                print(f"⚠️ Error processing document {doc.id}: {doc_error}")
                continue
        
        # Sort by timestamp (most recent first) in Python
        sessions_with_timestamps.sort(key=lambda x: x.get('_timestamp', 0), reverse=True)
        
        # Remove timestamp and limit results
        summaries = []
        for summary in sessions_with_timestamps[:limit]:
            summary.pop('_timestamp', None)
            summaries.append(summary)
        
        print(f"✅ Returning {len(summaries)} summaries for user {user_id}")
        return {"summaries": summaries}
        
    except Exception as e:
        print(f"❌ Error fetching summaries: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving summaries: {str(e)}"
        )


