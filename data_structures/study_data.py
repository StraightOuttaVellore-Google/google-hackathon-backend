from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class PomodoroTimer(BaseModel):
    work_time: int = Field(..., description="")
    break_time: int = Field(..., description="")
    no_of_iterations: int = Field(..., description="")
    # Preset 1
    work_time_preset1: Optional[int] = Field(..., description="")
    break_time_preset1: Optional[int] = Field(..., description="")
    no_of_iterations1: Optional[int] = Field(..., description="")
    # Preset 2
    work_time_preset2: Optional[int] = Field(..., description="")
    break_time_preset2: Optional[int] = Field(..., description="")
    no_of_iterations2: Optional[int] = Field(..., description="")
    # Preset 3
    work_time_preset3: Optional[int] = Field(..., description="")
    break_time_preset3: Optional[int] = Field(..., description="")
    no_of_iterations3: Optional[int] = Field(..., description="")


class TypeOfSound(Enum):
    AMBIENT = "ambient"
    NOISE = "noise"


class Noises(Enum):
    WHITE = "white"
    BLACK = "black"
    PINK = "pink"
    BROWN = "brown"


class Ambient(Enum):
    FOREST = "forest"
    RAIN = "rain"
    CITY = "city"
    OCEAN = "ocean"
    CAFE_CHATTER = "cafe_chatter"


class SoundPreset(BaseModel):
    class_of_noise: TypeOfSound = Field(default=TypeOfSound.AMBIENT, description="")
    sub_classification: Noises | Ambient = Field(defaut=Ambient.FOREST, description="")


class Sound(BaseModel):
    class_of_noise: TypeOfSound = Field(default=TypeOfSound.AMBIENT, description="")
    sub_classification: Noises | Ambient = Field(defaut=Ambient.FOREST, description="")
    favorite_1: Optional[SoundPreset] = Field(default=None, description="")
    favorite_2: Optional[SoundPreset] = Field(default=None, description="")
    favorite_3: Optional[SoundPreset] = Field(default=None, description="")


class TaskQuadrant(Enum):
    HUHI = "high_urgency_high_importanct"
    LUHI = "low_urgency_high_importanct"
    HULI = "high_urgency_low_importanct"
    LULI = "low_urgency_low_importanct"


class TaskStatus(Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Task(BaseModel):
    id: str = Field(..., description="firestore-doc-id")
    title: str = Field(..., description="Title of the task that will be displayed")
    description: str = Field(..., description="The detailed description of the task")
    quadrant: TaskQuadrant = Field(
        default=TaskQuadrant.HUHI, description="Level of urgency and importance"
    )
    status: TaskStatus = Field(
        default=TaskStatus.CREATED, description="The status of the task"
    )
    created_at: str = Field(
        ...,
        description="Required to enter the date of creation using the ISO 8601 format by using datetime.datetime.now().isoformat()",
    )
    updated_at: str = Field(
        ...,
        description="Required to enter the date of updation using the ISO 8601 format by using datetime.datetime.now().isoformat()",
    )


class EisenhowerMatrix(BaseModel):
    list_of_tasks: List[Task]


class StudyEmoji(Enum):
    RELAXED = "😌"  # almost no study, chilled day
    BALANCED = "🙂"  # light productive day, some balance
    FOCUSED = "📚"  # good study flow, but healthy
    INTENSE = "🔥"  # long study sessions, high energy
    OVERWHELMED = "😵"  # studied a lot, but mentally drained
    BURNT_OUT = "💀"  # extreme overload, unhealthy


# We do not store transcript and convo audio as we value the privacy of the user
class DailyData(BaseModel):
    day: int = Field(..., description="The day of journalling")
    month: int = Field(..., description="The month of journalling")
    year: int = Field(..., description="The year of journalling")
    emoji: StudyEmoji = Field(..., description="The emoji assigned for the day")
    summary: str = Field(..., description="Summary of the conversation with the agent")


class StudyData(BaseModel):
    pomodoro_timer: PomodoroTimer = Field(..., description="The pomodoro timer class")
    sound: Sound = Field(..., description="The ambient sound and colored noises class")
    eisenhower_matrix: EisenhowerMatrix = Field(
        ..., description="The eisenhower matrix for task list"
    )
    stress_jounral_data: List[DailyData] = Field(
        ..., description="List of the voice agent convo data over the days"
    )
