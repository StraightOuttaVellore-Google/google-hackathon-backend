"""
Firebase Firestore Document Models

These are Pydantic models that represent Firestore document structures.
They replace SQLModel for Firestore-based storage.

Note: Firestore stores documents as dictionaries, so these models are
used for validation and type hints, not as ORM-like objects.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
from datetime import datetime, date
from enum import Enum
import uuid


# ============================================================================
# USER MODELS
# ============================================================================

class TypesOfCustomers(str, Enum):
    FREE = "free"
    PRO = "pro"
    MAX = "max"


class UserDocument(BaseModel):
    """Firestore document structure for users collection"""
    user_id: str  # Document ID
    username: str
    email: EmailStr
    password: str  # Hashed
    type_of_customer: TypesOfCustomers
    created_at: datetime


# ============================================================================
# VOICE JOURNAL MODELS
# ============================================================================

class WellnessMode(str, Enum):
    STUDY = "study"
    WELLNESS = "wellness"


class VoiceJournalSessionDocument(BaseModel):
    """Firestore document structure for voiceJournalSessions collection"""
    session_id: str  # Document ID
    user_id: str
    mode: str  # "study" or "wellness"
    transcript: Optional[str] = None
    duration_seconds: Optional[int] = None
    analysis_completed: bool = False
    analysis_data: Optional[Dict] = None
    created_at: datetime


# ============================================================================
# WELLNESS MODELS
# ============================================================================

class Quadrant(str, Enum):
    HIHU = "high_imp_high_urg"
    LIHU = "low_imp_high_urg"
    HILU = "high_imp_low_urg"
    LILU = "low_imp_low_urg"


class TaskStatus(str, Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


class WellnessPathwayStatus(str, Enum):
    SUGGESTED = "suggested"
    REGISTERED = "registered"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AgentRecommendedTaskDocument(BaseModel):
    """Firestore document structure for agentRecommendedTasks collection"""
    task_id: str  # Document ID
    user_id: str
    task_title: str
    task_description: str
    quadrant: Quadrant
    status: TaskStatus = TaskStatus.TODO
    due_date: str  # ISO date string (YYYY-MM-DD)
    from_agent_session: Optional[str] = None
    created_at: datetime


class WellnessPathwayDocument(BaseModel):
    """Firestore document structure for wellnessPathways collection"""
    pathway_id: str  # Document ID
    user_id: str
    pathway_name: str
    pathway_type: str
    description: str
    duration_days: int = 7
    status: WellnessPathwayStatus = WellnessPathwayStatus.SUGGESTED
    progress_percentage: int = 0
    started_date: Optional[str] = None  # ISO date string
    completed_date: Optional[str] = None  # ISO date string
    metadata: Optional[Dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================================
# PRIORITY MATRIX MODELS
# ============================================================================

class PriorityMatrixTaskDocument(BaseModel):
    """Firestore document structure for priorityMatrix collection"""
    task_id: str  # Document ID
    user_id: str
    quadrant: Quadrant
    title: str
    description: str
    status: TaskStatus = TaskStatus.TODO
    due_date: Optional[str] = None  # ISO date string
    created_at: str  # ISO date string


# ============================================================================
# DAILY JOURNAL MODELS
# ============================================================================

class DailyJournalDataDocument(BaseModel):
    """Firestore document structure for dailyJournalData collection"""
    journal_id: str  # Document ID (format: {user_id}_{date})
    user_id: str
    journal_date: str  # ISO date string (YYYY-MM-DD)
    study_mode: bool = True
    mood: Optional[str] = None
    stress_level: Optional[int] = None  # 1-10 scale
    notes: Optional[str] = None
    data: Optional[Dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================================
# POMODORO MODELS
# ============================================================================

class PomodoroSessionDocument(BaseModel):
    """Firestore document structure for pomodoroSessions collection"""
    session_id: str  # Document ID
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    cycles_completed: int = 0
    created_at: datetime


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def datetime_to_firestore_timestamp(dt: datetime):
    """Convert Python datetime to Firestore timestamp"""
    from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    if dt is None:
        return SERVER_TIMESTAMP
    return dt


def firestore_timestamp_to_datetime(timestamp):
    """Convert Firestore timestamp to Python datetime"""
    if timestamp is None:
        return None
    
    # Firestore timestamps have a timestamp() method
    if hasattr(timestamp, 'timestamp'):
        return timestamp.timestamp()
    
    return timestamp


def document_to_dict(doc_snapshot, doc_id_field: str = "id") -> Dict:
    """
    Convert Firestore document snapshot to dictionary.
    
    Args:
        doc_snapshot: Firestore document snapshot
        doc_id_field: Field name to store document ID (default: "id")
    
    Returns:
        dict: Document data with ID included
    """
    if not doc_snapshot.exists:
        return None
    
    data = doc_snapshot.to_dict()
    data[doc_id_field] = doc_snapshot.id
    
    # Convert Firestore timestamps to datetime
    for key, value in data.items():
        if hasattr(value, 'timestamp'):
            data[key] = value
    
    return data

