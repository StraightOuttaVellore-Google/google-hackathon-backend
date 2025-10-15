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


class DeleteTaskData(BaseModel):
    id: str
