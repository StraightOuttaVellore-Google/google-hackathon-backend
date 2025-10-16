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
    title: str = Field(index=True)
    description: str
    status: TaskStatus = Field(default=TaskStatus.TODO)
    created_at: Optional[date] = Field(
        sa_column=Column(
            DATE,
            nullable=False,
            server_default=text("CURRENT_DATE"),
        )
    )


class TaskData(BaseModel):
    id: str
    quadrant: Quadrant
    title: str
    description: str
    status: Optional[TaskStatus] = TaskStatus.TODO


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
