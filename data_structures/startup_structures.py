from pydantic import BaseModel, Field, AnyUrl, field_validator
from enum import Enum
from typing import Optional
from data_structures.wellness_data import WellnessData
from data_structures.study_data import StudyData


class AvatarUrl(BaseModel):
    gcs_path: AnyUrl

    @field_validator("gcs_path")
    @classmethod
    def must_be_gcs_url(cls, v: AnyUrl):
        """Validate that the URL is a valid GCS path."""
        if v.scheme != "gs":
            raise ValueError("URL scheme must be 'gs'")
        if not v.host:
            raise ValueError("GCS URL must include a bucket name")
        return v


class Theme(Enum):
    DARK = "dark"
    LIGHT = "light"


class UserProfile(BaseModel):
    user_id: str = Field(
        ...,
        description="Used to uniquely identify a user. Unique Property.",
        alias="userId",
    )
    username: str = Field(..., description="Username of the user. Unique Property")
    display_name: str = Field(
        ...,
        description="Name that will be displayed on the webpage",
        alias="displayName",
    )
    avatar_url: Optional[str] = Field(
        default=None,
        description="URL used to retrieve users Display Image",
        alias="avatarUrl",
    )
    total_fished: int = Field(
        ..., description="No of fishes earned by the user", alias="totalFishes"
    )
    default_theme: Theme = Field(
        default=Theme.DARK, description="The system theme of the app"
    )

    model_config = {"populate_by_name": True}


class StartupData(BaseModel):
    user_profile_data: UserProfile = Field(..., description="")
    study_data: StudyData = Field(..., description="")
    wellness_data: WellnessData = Field(..., description="")
