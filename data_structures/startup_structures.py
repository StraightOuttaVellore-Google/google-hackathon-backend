from pydantic import BaseModel, Field, AnyUrl, field_validator
from typing import Optional
from wellness_data import WellnessData
from study_data import StudyData


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


class UserProfile(BaseModel):
    user_id: str = Field(
        ..., description="Used to uniquely identify a user. Unique Property."
    )
    username: str = Field(..., description="Username of the user. Unique Property")
    display_name: str = Field(
        ..., description="Name that will be displayed on the webpage"
    )
    avatar_url: Optional[AvatarUrl] = Field(
        default=None, description="URL used to retrieve users Display Image"
    )
    total_fished: int = Field(..., description="No of fishes earned by the user")


class StartupData(BaseModel):
    user_profile_data: UserProfile = Field(..., description="")
    study_data: StudyData = Field(..., description="")
    wellness_data: WellnessData = Field(..., description="")
