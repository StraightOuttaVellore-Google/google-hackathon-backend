from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    UploadFile,
    File,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
from datetime import datetime

# Import data structures
from data_structures.startup_structures import StartupData, UserProfile
from data_structures.study_data import StudyData, Task
from data_structures.wellness_data import WellnessData, DailyData

app = FastAPI(title="Wellness & Study App API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Response models
class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: str


class VoiceJournalResponse(BaseModel):
    success: bool = True
    entryId: str
    transcript: str
    summary: str
    moodTags: List[str]
    riskAssessment: str


class ChatResponse(BaseModel):
    success: bool = True
    aiResponse: str


class PostsResponse(BaseModel):
    posts: List[Dict[str, Any]]


# Request models
class SyncRequest(BaseModel):
    user_profile: Optional[UserProfile] = None
    study_data: Optional[StudyData] = None
    wellness_data: Optional[WellnessData] = None
    community_data: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    conversationId: str
    content: str


# Mock authentication middleware
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Extract user ID from JWT token.
    In production, validate the Supabase JWT token here.
    """
    # Mock implementation - replace with actual JWT validation
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return "mock-user-id"  # Return actual user ID from token


# Mock data store (replace with Firestore in production)
mock_data = {
    "users": {
        "mock-user-id": {
            "user_profile": {
                "userId": "mock-user-id",
                "username": "john_doe",
                "displayName": "John Doe",
                "avatarUrl": "gs://bucket/avatar.jpg",
                "totalFishes": 42,
            },
            "study_data": {"eisenhower_tasks": [], "chat_conversations": []},
            "wellness_data": {
                "daily_moods_current_month": [],
                "active_pathways": [],
                "recent_journals": [],
            },
            "community_data": {"user_groups": []},
        }
    }
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_id: str):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)

    def disconnect(self, websocket: WebSocket, group_id: str):
        if group_id in self.active_connections:
            self.active_connections[group_id].remove(websocket)

    async def send_message(self, message: str, group_id: str):
        if group_id in self.active_connections:
            for connection in self.active_connections[group_id]:
                await connection.send_text(message)


manager = ConnectionManager()

# Session-Based Endpoints


@app.get("/api/v1/user/startup", response_model=Dict[str, Any])
async def get_startup_data(current_user: str = Depends(get_current_user)):
    """
    Get all initial data for the user's session.
    """
    try:
        user_data = mock_data["users"].get(current_user)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        return user_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/user/sync", response_model=SuccessResponse)
async def sync_user_data(
    sync_data: SyncRequest, current_user: str = Depends(get_current_user)
):
    """
    Sync updated user data back to the database.
    """
    try:
        if current_user not in mock_data["users"]:
            mock_data["users"][current_user] = {}

        user_data = mock_data["users"][current_user]

        # Update data based on what's provided
        if sync_data.user_profile:
            user_data["user_profile"] = sync_data.user_profile.model_dump()
        if sync_data.study_data:
            user_data["study_data"] = sync_data.study_data.model_dump()
        if sync_data.wellness_data:
            user_data["wellness_data"] = sync_data.wellness_data.model_dump()
        if sync_data.community_data:
            user_data["community_data"] = sync_data.community_data

        return SuccessResponse(message="Data synced successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Specialized Endpoints


@app.post("/api/v1/wellness/voice-journal", response_model=VoiceJournalResponse)
async def process_voice_journal(
    audio: UploadFile = File(...),
    title: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Process voice journaling upload and return AI analysis.
    """
    try:
        # Mock processing - replace with actual audio processing and AI analysis
        entry_id = f"entry_{datetime.now().timestamp()}"

        # Simulate AI processing
        mock_transcript = "Today I felt really good about completing my tasks..."
        mock_summary = "User expressed positive feelings about productivity"
        mock_mood_tags = ["happy", "motivated"]
        mock_risk_assessment = "low"

        return VoiceJournalResponse(
            entryId=entry_id,
            transcript=mock_transcript,
            summary=mock_summary,
            moodTags=mock_mood_tags,
            riskAssessment=mock_risk_assessment,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/study/chat/message", response_model=ChatResponse)
async def send_chat_message(
    message: ChatMessage, current_user: str = Depends(get_current_user)
):
    """
    Send a message to the AI assistant and get a response.
    """
    try:
        # Mock AI response - replace with actual AI model integration
        ai_response = f"Based on your message '{message.content}', I recommend focusing on your high-priority tasks first."

        return ChatResponse(aiResponse=ai_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/wellness/world/posts", response_model=PostsResponse)
async def get_community_posts(current_user: str = Depends(get_current_user)):
    """
    Get posts from the wellness community world.
    """
    try:
        # Mock community posts - replace with actual database query
        mock_posts = [
            {
                "id": "post1",
                "author": "user123",
                "content": "Just completed my meditation pathway!",
                "timestamp": datetime.now().isoformat(),
                "likes": 15,
            },
            {
                "id": "post2",
                "author": "user456",
                "content": "Having a great study session today",
                "timestamp": datetime.now().isoformat(),
                "likes": 8,
            },
        ]

        return PostsResponse(posts=mock_posts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/wellness/world/posts", response_model=SuccessResponse)
async def create_community_post(
    post_data: Dict[str, Any], current_user: str = Depends(get_current_user)
):
    """
    Create a new community post.
    """
    try:
        # Mock post creation - replace with actual database operation
        post_id = f"post_{datetime.now().timestamp()}"

        return SuccessResponse(message=f"Post created with ID: {post_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/wellness/world/posts/{post_id}/like", response_model=SuccessResponse)
async def like_community_post(
    post_id: str, current_user: str = Depends(get_current_user)
):
    """
    Like a community post.
    """
    try:
        # Mock like operation - replace with actual database operation
        return SuccessResponse(message=f"Post {post_id} liked successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket Endpoint


@app.websocket("/ws/community/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: str):
    """
    WebSocket endpoint for real-time community chat.
    """
    # In production, validate JWT token from query parameters
    await manager.connect(websocket, group_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Broadcast message to all users in the group
            await manager.send_message(data, group_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
