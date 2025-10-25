from datetime import date, datetime
from enum import Enum
from sqlmodel import Field, SQLModel, Column, TIMESTAMP, text, DATE, UUID
from typing import Optional, Dict
from sqlalchemy.dialects import postgresql
from pydantic import BaseModel, EmailStr
import uuid


class TypesOfCustomers(str, Enum):
    FREE = "free"
    PRO = "pro"
    MAX = "max"


class Users(SQLModel, table=True):
    user_id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(unique=True)
    password: str
    type_of_customer: TypesOfCustomers
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str
    username: str
    type_of_customer: TypesOfCustomers


class SignupData(BaseModel):
    username: str
    email: EmailStr
    password: str


class JournalSummaries(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id")
    study_mode: bool
    data: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class JournalSummariesInput(BaseModel):
    study_mode: bool
    data: Optional[Dict]


class Quadrant(str, Enum):
    HIHU = "high_imp_high_urg"
    LIHU = "low_imp_high_urg"
    HILU = "high_imp_low_urg"
    LILU = "low_imp_low_urg"


class TaskStatus(str, Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


class PriorityMatrix(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id")
    quadrant: Quadrant
    title: str
    description: str
    status: TaskStatus = Field(default=TaskStatus.TODO)
    # Optional due date to integrate with calendar views
    due_date: Optional[date] = Field(
        default=None,
        sa_column=Column(
            DATE,
            nullable=True,
        ),
    )
    created_at: Optional[date] = Field(
        sa_column=Column(
            DATE,
            nullable=False,
            server_default=text("CURRENT_DATE"),
        )
    )


class TaskData(BaseModel):
    id: Optional[str] = None
    quadrant: Quadrant
    title: str
    description: str
    status: Optional[TaskStatus] = TaskStatus.TODO
    # ISO date string (YYYY-MM-DD) for the task's due date
    due_date: Optional[date] = None


class DeleteTaskData(BaseModel):
    id: str


# Chat Models
class ChannelType(str, Enum):
    TEXT = "text"
    VOICE = "voice"


class ServerRole(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"


class ChatServer(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    name: str = Field(index=True, unique=True)
    icon: str  # emoji or icon identifier
    created_by: uuid.UUID = Field(foreign_key="users.user_id")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class ChatChannel(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    server_id: uuid.UUID = Field(foreign_key="chatserver.id", index=True)
    name: str
    type: ChannelType
    position: int = Field(default=0)
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class ChatMessage(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    server_id: uuid.UUID = Field(foreign_key="chatserver.id", index=True)
    channel_id: uuid.UUID = Field(foreign_key="chatchannel.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    text: str
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class ServerMembership(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    server_id: uuid.UUID = Field(foreign_key="chatserver.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    role: ServerRole = Field(default=ServerRole.MEMBER)
    joined_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


# Pydantic models for Chat API
class CreateServerData(BaseModel):
    name: str
    icon: str


class CreateChannelData(BaseModel):
    name: str
    type: ChannelType


class SendMessageData(BaseModel):
    text: str


class AddMemberData(BaseModel):
    user_id: str
    role: Optional[ServerRole] = ServerRole.MEMBER


class ServerResponse(BaseModel):
    id: str
    name: str
    icon: str
    created_by: str
    created_at: datetime


class ChannelResponse(BaseModel):
    id: str
    server_id: str
    name: str
    type: ChannelType
    position: int


class MessageResponse(BaseModel):
    id: str
    user: str  # username
    text: str
    timestamp: str
    server_id: str
    channel_id: str


# Pomodoro Settings
class PomodoroSettings(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id", unique=True)
    work_duration: int = Field(default=25)  # minutes
    short_break: int = Field(default=5)  # minutes
    long_break: int = Field(default=15)  # minutes
    sessions_before_long_break: int = Field(default=4)
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class PomodoroSettingsInput(BaseModel):
    work_duration: Optional[int] = None
    short_break: Optional[int] = None
    long_break: Optional[int] = None
    sessions_before_long_break: Optional[int] = None


# Sound Preferences
class SoundPreferences(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id", unique=True)
    selected_sound: str = Field(default="none")
    volume: float = Field(default=0.5)
    is_playing: bool = Field(default=False)
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class SoundPreferencesInput(BaseModel):
    selected_sound: Optional[str] = None
    volume: Optional[float] = None
    is_playing: Optional[bool] = None


# Daily Journal Data
class DailyJournalData(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id")
    journal_date: date = Field(sa_column=Column(DATE, nullable=False, index=True))
    study_mode: bool = Field(default=True)
    mood: Optional[str] = None
    stress_level: Optional[int] = None  # 1-10 scale
    notes: Optional[str] = None
    data: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class DailyJournalDataInput(BaseModel):
    journal_date: str  # ISO date format YYYY-MM-DD
    study_mode: bool
    mood: Optional[str] = None
    stress_level: Optional[int] = None
    notes: Optional[str] = None
    data: Optional[Dict] = None


# Moodboard Data
class MoodboardData(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id", unique=True)
    study_mode: bool = Field(default=True)
    data: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class MoodboardDataInput(BaseModel):
    study_mode: bool
    data: Optional[Dict] = None


# Sound Usage Statistics
class SoundUsageLog(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id")
    sound_type: str  # "ambient" or "noise"
    sound_name: str  # "white", "forest", "rain", etc.
    started_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    ended_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=True,
        )
    )
    duration_seconds: Optional[int] = None  # calculated field
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class SoundUsageLogInput(BaseModel):
    sound_type: str
    sound_name: str


class EndSoundSessionInput(BaseModel):
    pass


# Pomodoro Usage Statistics
class PomodoroSession(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id")
    started_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    ended_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=True,
        )
    )
    duration_seconds: Optional[
        int
    ] = None  # Total duration including all pomodoro cycles
    cycles_completed: int = Field(default=0)  # Number of pomodoro cycles completed
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class PomodoroSessionInput(BaseModel):
    pass
<<<<<<< HEAD
=======


# Wearable Device Models
class WearableDeviceType(str, Enum):
    SMART_WATCH = "smart_watch"
    FITNESS_TRACKER = "fitness_tracker"
    SMART_GLASSES = "smart_glasses"
    RING = "ring"


class WearableDevice(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id")
    device_type: WearableDeviceType
    device_name: str  # "Apple Watch Series 9", "Fitbit Sense 2"
    device_id: str  # Unique device identifier
    is_active: bool = Field(default=True)
    last_sync: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=True,
        )
    )
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class WearableData(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id")
    device_id: uuid.UUID = Field(foreign_key="wearabledevice.id", index=True)
    data_date: date = Field(sa_column=Column(DATE, nullable=False, index=True))
    
    # Sleep Data (HIGH PRIORITY)
    sleep_duration_hours: Optional[float] = None
    sleep_efficiency: Optional[float] = None  # 0-1 scale
    deep_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    light_sleep_hours: Optional[float] = None
    sleep_score: Optional[int] = None  # 1-100
    bedtime: Optional[datetime] = None
    wake_time: Optional[datetime] = None
    
    # Heart Rate Data (HIGH PRIORITY)
    avg_heart_rate: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    hrv_rmssd: Optional[float] = None  # Heart Rate Variability
    hrv_z_score: Optional[float] = None  # Z-score for HRV
    
    # Activity Data (HIGH PRIORITY)
    steps: Optional[int] = None
    calories_burned: Optional[int] = None
    active_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    floors_climbed: Optional[int] = None
    
    # Stress & Recovery (HIGH PRIORITY)
    stress_score: Optional[float] = None  # 0-1 scale
    stress_events: Optional[int] = None  # Number of stress events
    recovery_score: Optional[int] = None  # 1-100
    energy_level: Optional[str] = None  # "low", "medium", "high"
    
    # Environmental Data (MEDIUM PRIORITY)
    ambient_temperature: Optional[float] = None
    humidity: Optional[float] = None
    noise_level: Optional[float] = None  # dB
    light_level: Optional[str] = None  # "low", "medium", "high"
    
    # Additional Metrics
    breathing_rate: Optional[float] = None
    blood_oxygen: Optional[float] = None  # SpO2
    
    # Raw data storage for complex metrics
    raw_data: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class WearableInsights(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(index=True, foreign_key="users.user_id")
    insight_date: date = Field(sa_column=Column(DATE, nullable=False, index=True))
    insight_type: str  # "recovery_score", "stress_analysis", "focus_recommendation", "sleep_analysis"
    
    # Core Insights
    overall_recovery_score: Optional[int] = None  # 1-100
    sleep_debt_hours: Optional[float] = None
    stress_level: Optional[str] = None  # "low", "medium", "high"
    focus_recommendation: Optional[str] = None  # "high", "medium", "low"
    
    # AI-Generated Insights
    ai_insights: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    confidence_score: Optional[float] = None  # 0-1
    
    # Recommendations
    recommended_focus_duration: Optional[int] = None  # minutes
    recommended_break_duration: Optional[int] = None  # minutes
    recommended_activities: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


# Pydantic Models for API
class WearableDeviceInput(BaseModel):
    device_type: WearableDeviceType
    device_name: str
    device_id: str


class WearableDataInput(BaseModel):
    device_id: str
    data_date: str  # ISO date format YYYY-MM-DD
    
    # Sleep Data
    sleep_duration_hours: Optional[float] = None
    sleep_efficiency: Optional[float] = None
    deep_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    light_sleep_hours: Optional[float] = None
    sleep_score: Optional[int] = None
    bedtime: Optional[str] = None  # ISO datetime
    wake_time: Optional[str] = None  # ISO datetime
    
    # Heart Rate Data
    avg_heart_rate: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    hrv_rmssd: Optional[float] = None
    hrv_z_score: Optional[float] = None
    
    # Activity Data
    steps: Optional[int] = None
    calories_burned: Optional[int] = None
    active_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    floors_climbed: Optional[int] = None
    
    # Stress & Recovery
    stress_score: Optional[float] = None
    stress_events: Optional[int] = None
    recovery_score: Optional[int] = None
    energy_level: Optional[str] = None
    
    # Environmental Data
    ambient_temperature: Optional[float] = None
    humidity: Optional[float] = None
    noise_level: Optional[float] = None
    light_level: Optional[str] = None
    
    # Additional Metrics
    breathing_rate: Optional[float] = None
    blood_oxygen: Optional[float] = None
    
    # Raw data
    raw_data: Optional[Dict] = None


class WearableAnalysisRequest(BaseModel):
    data_date: str
    analysis_type: str  # "comprehensive", "stress_focus", "sleep_recovery"
    include_recommendations: bool = True


class WearableInsightsResponse(BaseModel):
    insight_date: str
    overall_recovery_score: int
    sleep_debt_hours: float
    stress_level: str
    focus_recommendation: str
    ai_insights: Dict
    confidence_score: float
    recommended_focus_duration: int
    recommended_break_duration: int
    recommended_activities: Dict
>>>>>>> origin/main
