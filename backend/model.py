from datetime import date, datetime
from enum import Enum
from sqlmodel import Field, SQLModel, Column, TIMESTAMP, text, DATE
from typing import Optional, Dict
from sqlalchemy.dialects import postgresql


class JounralSummaries(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_name: str = Field(index=True)
    study_mode: bool
    data: Optional[Dict] = Field(default=None, sa_column=Column(postgresql.JSONB))
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class Quadrant(str, Enum):
    HIHU = "high_imp_high_urg"
    LIHU = "low_imp_high_urg"
    HILU = "high_imp_low_urg"
    LILU = "low_imp_low_urg"


class PriorityMatrix(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_name: str = Field(index=True)
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
