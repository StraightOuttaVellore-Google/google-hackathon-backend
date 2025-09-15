from sys import deactivate_stack_trampoline
from pydantic import AnyUrl, BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum


class NodeCompletionStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PathwayNode(BaseModel):
    node_id: int = Field(..., description="The position of the node in the pathway")
    link_to_node: AnyUrl = Field(..., description="The link to the node")
    title: str = Field(..., description="Title of the webpage")
    description: str = Field(..., description="Provides a description to the end user")
    node_info: Optional[Dict] = Field(
        ...,
        description="A Dictionary to store any kind of information required for the node",
    )
    node_completion: NodeCompletionStatus = Field(
        default=NodeCompletionStatus.NOT_STARTED, description=""
    )


class PathwayProgress(BaseModel):
    is_enrolled: bool = Field(
        default=False, description="Is the user enrolled in the pathway"
    )
    current_node: int = Field(default=1, description="The node on which the user is")
    completed_nodes: List[int] = Field(
        default=[], description="List of all the nodes completed"
    )


class Pathway(BaseModel):
    id: str = Field(..., description="The id of the pathway")
    title: str = Field(..., description="The title of the pathway")
    description: str = Field(..., description="Provides a description to the end user")
    category: str = Field(..., description="The category of the pathway")
    total_nodes: int = Field(..., description="Number of nodes in the pathway")
    nodes_in_path: List[PathwayNode] = Field(
        ..., description="List of all the nodes in the pathway"
    )
    pathway_progress: List[PathwayProgress] = Field(
        ..., description="The pathway progress of the user"
    )


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
    pathways: List[Pathway]
    welness_journal_data: List[DailyData] = Field(
        ..., description="List of the voice agent convo data over the days"
    )
