from datetime import datetime
from sqlmodel import Field, SQLModel, Column, TIMESTAMP, text
from typing import Optional
from pydantic import BaseModel


class JounralSummaries(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_name: str = Field(index=True)
    summary: str
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
