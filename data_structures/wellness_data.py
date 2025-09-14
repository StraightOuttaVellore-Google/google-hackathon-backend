from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class WellnessEmoji(Enum):
    JOYFUL = "😄"  # very happy, upbeat
    CONTENT = "😊"  # calm, satisfied
    NEUTRAL = "😐"  # okay, nothing special
    LOW = "😔"  # a bit down or sad
    ANXIOUS = "😰"  # worried, uneasy
    DEPRESSED = "😭"  # very low emotional state


# We do not store transcript and convo audio as we value the privacy of the user
class DailyData(BaseModel):
    day: int = Field(..., description="The day of journalling")
    month: int = Field(..., description="The month of journalling")
    year: int = Field(..., description="The year of journalling")
    emoji: WellnessEmoji = Field(..., description="The emoji assigned for the day")
    summary: str = Field(..., description="Summary of the conversation with the agent")


class WellnessData(BaseModel):
    welness_journal_data: List[DailyData] = Field(
        ..., description="List of the voice agent convo data over the days"
    )
