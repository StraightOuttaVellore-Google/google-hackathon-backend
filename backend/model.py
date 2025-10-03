from datetime import datetime
from sqlmodel import Field, SQLModel, Column, TIMESTAMP, text
from typing import Optional, Dict, Any
from pydantic import BaseModel
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


class HTTPResponse(BaseModel):
    status: int
    message: str
