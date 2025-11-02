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


# Reddit Models
class Country(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    iso_code: str = Field(index=True, unique=True, max_length=3)  # e.g., 'US', 'IN', 'GB'
    name: str = Field(max_length=100)
    flag_emoji: Optional[str] = Field(default=None, max_length=10)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class RedditPost(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    country_id: uuid.UUID = Field(foreign_key="country.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    title: str = Field(max_length=300)
    content: str
    media_urls: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    score: int = Field(default=0)
    comment_count: int = Field(default=0)
    is_pinned: bool = Field(default=False)
    is_hidden: bool = Field(default=False)
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


class RedditComment(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    post_id: uuid.UUID = Field(foreign_key="redditpost.id", index=True)
    parent_id: Optional[uuid.UUID] = Field(foreign_key="redditcomment.id", default=None, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    content: str
    score: int = Field(default=0)
    is_hidden: bool = Field(default=False)
    depth: int = Field(default=0)
    path: Optional[str] = None  # Materialized path for efficient queries
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


class RedditVote(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    post_id: Optional[uuid.UUID] = Field(foreign_key="redditpost.id", default=None, index=True)
    comment_id: Optional[uuid.UUID] = Field(foreign_key="redditcomment.id", default=None, index=True)
    vote_type: int = Field()  # 1 for upvote, -1 for downvote
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class CountrySubscription(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    country_id: uuid.UUID = Field(foreign_key="country.id", index=True)
    subscribed_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class CountryRole(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"


class RedditCountryRole(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    user_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    country_id: uuid.UUID = Field(foreign_key="country.id", index=True)
    role: CountryRole = Field(default=CountryRole.MEMBER)
    assigned_by: Optional[uuid.UUID] = Field(foreign_key="users.user_id", default=None)
    assigned_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class RedditReport(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        )
    )
    reporter_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    post_id: Optional[uuid.UUID] = Field(foreign_key="redditpost.id", default=None, index=True)
    comment_id: Optional[uuid.UUID] = Field(foreign_key="redditcomment.id", default=None, index=True)
    reason: str = Field(max_length=100)
    description: Optional[str] = None
    status: str = Field(default="pending", max_length=20)  # 'pending', 'resolved', 'dismissed'
    reviewed_by: Optional[uuid.UUID] = Field(foreign_key="users.user_id", default=None)
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


# Wellness Agent Models for Voice Journal Analysis

class WellnessMode(str, Enum):
    """Mode determines which agent system to activate"""
    STUDY = "study"  # Academic stress management
    WELLNESS = "wellness"  # General wellness (matches voice_agent.py)

class WellnessPathwayStatus(str, Enum):
    SUGGESTED = "suggested"
    REGISTERED = "registered"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class WellnessPathway(SQLModel, table=True):
    """Wellness pathways suggested by agents and tracked for users"""
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
    pathway_name: str
    pathway_type: str  # mindfulness, exercise, study_technique, stress_management, etc.
    description: str
    duration_days: int = Field(default=7)  # Default 1 week pathway
    status: WellnessPathwayStatus = Field(default=WellnessPathwayStatus.SUGGESTED)
    progress_percentage: int = Field(default=0)
    started_date: Optional[date] = None
    completed_date: Optional[date] = None
    extra_data: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))  # Renamed from 'metadata' to avoid SQLModel conflict
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


class AgentRecommendedTask(SQLModel, table=True):
    """Tasks recommended by wellness agents"""
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
    task_title: str
    task_description: str
    quadrant: Quadrant  # Maps to Eisenhower Matrix
    status: TaskStatus = Field(default=TaskStatus.TODO)
    due_date: date  # Auto-calculated based on urgency
    from_agent_session: Optional[uuid.UUID] = None  # Links to journal analysis
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


# Voice Journal Session Model (links transcript to analysis)
class VoiceJournalSession(SQLModel, table=True):
    """Track voice journal sessions and their analysis"""
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
    mode: str  # "study" or "wellness"
    transcript: Optional[str] = None  # Full transcript from session
    duration_seconds: Optional[int] = None
    analysis_completed: bool = Field(default=False)
    analysis_data: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


# Pydantic models for agent outputs
class WellnessRecommendation(BaseModel):
    title: str
    description: str
    category: str


class WellnessExercise(BaseModel):
    name: str
    instructions: str
    duration: str
    best_for: Optional[str] = None


class WellnessResource(BaseModel):
    type: str
    title: str
    description: str


class WellnessPathwayData(BaseModel):
    """Wellness pathway suggested by agent"""
    pathway_name: str
    pathway_type: str
    description: str
    duration_days: int = 7


class RecommendedTaskOutput(BaseModel):
    """Task output from agent"""
    task_title: str
    task_description: str
    priority_classification: str  # urgent_important, important_not_urgent, etc.
    suggested_due_days: int = 7  # Days from now


class TranscriptSummary(BaseModel):
    """Summary to display under transcript"""
    summary: str
    emotions: list[str]
    focus_areas: list[str]
    tags: list[str]
    stress_level: Optional[str] = None  # For study mode
    academic_concerns: Optional[list[str]] = None  # For study mode only


class StatsRecommendations(BaseModel):
    """Recommendations to show in stats/analysis area"""
    recommendations: list[WellnessRecommendation]
    wellness_exercises: list[WellnessExercise]
    resources: list[WellnessResource]
    wellness_pathways: list[WellnessPathwayData]  # NEW: Pathways user can register for
    recommended_tasks: list[RecommendedTaskOutput]  # Tasks for Eisenhower matrix
    tone: str
    study_focus_tips: Optional[list[str]] = None  # Study mode only


class VoiceJournalAnalysisResult(BaseModel):
    """Complete analysis result from wellness agents"""
    session_id: str
    mode: WellnessMode
    transcript_summary: TranscriptSummary  # Shows under transcript
    stats_recommendations: StatsRecommendations  # Shows in stats area
    safety_approved: bool
    safety_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TriggerAnalysisInput(BaseModel):
    """Input to trigger wellness analysis"""
    transcript: str
    mode: WellnessMode  # study or general
    user_id: str


class RegisterPathwayInput(BaseModel):
    """Register user for a wellness pathway"""
    pathway_name: str
    pathway_type: str
    description: str
    duration_days: int = 7


class AddAgentTaskInput(BaseModel):
    """Add task from agent recommendations to matrix"""
    task_title: str
    task_description: str
    quadrant: Quadrant
    due_days_from_now: int = 7




# Pydantic models for Reddit API
class CountryCreate(BaseModel):
    iso_code: str
    name: str
    flag_emoji: Optional[str] = None
    description: Optional[str] = None


class CountryResponse(BaseModel):
    id: str
    iso_code: str
    name: str
    flag_emoji: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime


class PostCreate(BaseModel):
    title: str
    content: str
    media_urls: Optional[Dict] = None


class PostResponse(BaseModel):
    id: str
    country_id: str
    country_name: str
    user_id: str
    username: str
    title: str
    content: str
    media_urls: Optional[Dict] = None
    score: int
    comment_count: int
    is_pinned: bool
    is_hidden: bool
    user_vote: Optional[int] = None  # 1, -1, or None
    created_at: datetime
    updated_at: datetime


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[str] = None


class CommentResponse(BaseModel):
    id: str
    post_id: str
    parent_id: Optional[str] = None
    user_id: str
    username: str
    content: str
    score: int
    is_hidden: bool
    depth: int
    user_vote: Optional[int] = None  # 1, -1, or None
    created_at: datetime
    updated_at: datetime


class VoteRequest(BaseModel):
    vote_type: int  # 1 for upvote, -1 for downvote


class ReportRequest(BaseModel):
    reason: str
    description: Optional[str] = None


class VoiceJournalSessionInput(BaseModel):
    """Input for creating a voice journal session"""
    mode: WellnessMode
    transcript: str
    duration_seconds: Optional[int] = None
