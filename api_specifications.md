# API Specifications - Hackathon Edition

## Overview
Simplified REST API endpoints for the Wellness & Study App hackathon project. All endpoints require authentication via Supabase JWT token. **No WebSocket connections needed** - keeping it simple!

## Base Configuration
- **Base URL**: `https://your-api-domain.com/api/v1`
- **Authentication**: Bearer token in Authorization header
- **Content-Type**: `application/json`
- **Database**: Google Cloud Firestore
- **File Storage**: Google Cloud Storage
- **Rate Limiting**: Basic (handled by Cloud Run)

## REST API Endpoints

### Authentication & User Management

#### **GET /user/startup**
Get all initial data needed for app startup (no user_id needed - extracted from JWT).

**Response:**
```json
{
  "user_profile": {
    "userId": "supabase-user-id",
    "username": "john_doe",
    "displayName": "John Doe",
    "avatarUrl": "gs://bucket/avatar.jpg",
    "totalFishes": 42
  },
  "study_data": {
    "activeTasks": [...],
    "completedTasksToday": 3
  },
  "wellness_data": {
    "todaysMood": {...},
    "activePathways": [...],
    "recentJournals": [...]
  }
}
```

#### **PUT /user/profile**
Update user profile information.

**Body:**
```json
{
  "displayName": "John Doe",
  "username": "john_doe",
  "avatarUrl": "gs://bucket/new-avatar.jpg"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Profile updated successfully"
}
```

---

### Study Mode APIs

#### **GET /study/tasks**
Get all tasks from Eisenhower matrix for the authenticated user.

**Query Parameters:**
- `quadrant` (optional): Filter by quadrant
- `status` (optional): Filter by status

**Response:**
```json
{
  "tasks": [
    {
      "id": "firestore-doc-id",
      "title": "Complete project proposal",
      "description": "Detailed description here",
      "quadrant": "urgent_important",
      "status": "pending",
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### **POST /study/tasks**
Create a new task in Eisenhower matrix.

**Body:**
```json
{
  "title": "Complete project proposal",
  "description": "Write the final draft of the project proposal",
  "quadrant": "urgent_important"
}
```

**Response:**
```json
{
  "success": true,
  "taskId": "firestore-doc-id"
}
```

#### **PUT /study/tasks/{task_id}**
Update an existing task.

**Parameters:**
- `task_id` (path): Firestore document ID

**Body:**
```json
{
  "title": "Updated task title",
  "description": "Updated description",
  "quadrant": "not_urgent_important",
  "status": "completed"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task updated successfully"
}
```

#### **DELETE /study/tasks/{task_id}**
Delete a task.

**Parameters:**
- `task_id` (path): Firestore document ID

**Response:**
```json
{
  "success": true,
  "message": "Task deleted successfully"
}
```

#### **POST /study/pomodoro-complete**
Record completion of a Pomodoro session (frontend handles timer).

**Body:**
```json
{
  "completedMinutes": 25,
  "fishesEarned": 5,
  "completedTaskIds": ["task1", "task2"]
}
```

**Response:**
```json
{
  "success": true,
  "newTotalFishes": 47,
  "message": "Pomodoro session recorded"
}
```

#### **GET /study/chat/conversations**
Get user's chat conversations with the AI assistant.

**Response:**
```json
{
  "conversations": [
    {
      "id": "firestore-doc-id",
      "title": "Daily Planning Chat",
      "lastMessage": "Thanks for the help!",
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### **POST /study/chat/conversations**
Create a new chat conversation.

**Body:**
```json
{
  "title": "Daily Planning",
  "initialMessage": "Help me organize my tasks for today"
}
```

**Response:**
```json
{
  "success": true,
  "conversationId": "firestore-doc-id",
  "aiResponse": "I'd be happy to help you organize your tasks! What do you need to accomplish today?"
}
```

#### **GET /study/chat/conversations/{conversation_id}**
Get a specific conversation with all messages.

**Parameters:**
- `conversation_id` (path): Firestore document ID

**Response:**
```json
{
  "conversation": {
    "id": "firestore-doc-id",
    "title": "Daily Planning Chat",
    "messages": [
      {
        "role": "user",
        "content": "Help me prioritize my tasks",
        "timestamp": "2024-01-01T10:00:00Z"
      },
      {
        "role": "assistant",
        "content": "I can help you prioritize! Let's use the Eisenhower Matrix...",
        "timestamp": "2024-01-01T10:00:05Z"
      }
    ],
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T10:00:05Z"
  }
}
```

#### **POST /study/chat/conversations/{conversation_id}/message**
Send a message to the AI assistant in an existing conversation.

**Parameters:**
- `conversation_id` (path): Firestore document ID

**Body:**
```json
{
  "content": "How should I prioritize my tasks today?"
}
```

**Response:**
```json
{
  "success": true,
  "aiResponse": "Based on your current tasks, I recommend focusing on the urgent-important quadrant first...",
  "updatedAt": "2024-01-01T10:05:00Z"
}
```

---

### Wellness Mode APIs

#### **POST /wellness/voice-journal**
Process voice journaling (upload audio, get AI analysis).

**Body:** `multipart/form-data`
- `audio`: Audio file (.wav, .mp3, .m4a)
- `title`: Optional title for the journal entry

**Response:**
```json
{
  "success": true,
  "entryId": "firestore-doc-id", 
  "transcript": "Today I felt really good about my progress...",
  "summary": "Positive reflection on daily progress and goals",
  "moodTags": ["happy", "motivated", "grateful"],
  "riskAssessment": "low",
  "dailyMoodUpdated": true
}
```

#### **GET /wellness/journal/entries**
Get user's journal entries.

**Query Parameters:**
- `limit` (optional): Number of entries (default: 10)
- `startDate` (optional): Filter from date (YYYY-MM-DD)
- `endDate` (optional): Filter to date (YYYY-MM-DD)

**Response:**
```json
{
  "entries": [
    {
      "id": "firestore-doc-id",
      "title": "Morning Reflection",
      "summary": "Positive day with good progress",
      "moodTags": ["happy", "motivated"],
      "riskAssessment": "low",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### **GET /wellness/journal/entries/{entry_id}**
Get detailed view of a specific journal entry.

**Parameters:**
- `entry_id` (path): Firestore document ID

**Response:**
```json
{
  "entry": {
    "id": "firestore-doc-id",
    "title": "Morning Reflection",
    "transcript": "Today I felt really good about my progress...",
    "summary": "Positive reflection on daily progress and goals",
    "moodTags": ["happy", "motivated", "grateful"],
    "riskAssessment": "low",
    "createdAt": "2024-01-01T00:00:00Z"
  }
}
```

#### **GET /wellness/mood/calendar**
Get mood data for calendar view.

**Query Parameters:**
- `year` (required): Year (e.g., 2024)
- `month` (required): Month (1-12)

**Response:**
```json
{
  "moodData": [
    {
      "date": "2024-01-01",
      "emoji": "😊",
      "summary": "Great day with good energy!",
      "tags": ["happy", "productive"]
    }
  ]
}
```

#### **GET /wellness/mood/summary**
Get mood summary for a specific date.

**Query Parameters:**
- `date` (required): Date in YYYY-MM-DD format

**Response:**
```json
{
  "date": "2024-01-01",
  "emoji": "😊",
  "summary": "Had a very productive day with good energy",
  "tags": ["happy", "productive", "grateful"],
  "journalEntries": [
    {
      "id": "firestore-doc-id",
      "title": "Morning Reflection",
      "createdAt": "2024-01-01T09:30:00Z"
    }
  ]
}
```

#### **GET /wellness/pathways**
Get available wellness pathways.

**Query Parameters:**
- `category` (optional): Filter by category

**Response:**
```json
{
  "pathways": [
    {
      "id": "anxiety-management-101",
      "title": "Managing Anxiety",
      "description": "A step-by-step guide to understanding and managing anxiety",
      "category": "anxiety",
      "totalNodes": 10,
      "userProgress": {
        "isEnrolled": true,
        "currentNode": 3,
        "completedNodes": [1, 2]
      }
    }
  ]
}
```

#### **POST /wellness/pathways/{pathway_id}/enroll**
Enroll in a wellness pathway.

**Parameters:**
- `pathway_id` (path): Pathway ID

**Response:**
```json
{
  "success": true,
  "message": "Enrolled in pathway successfully"
}
```

#### **GET /wellness/pathways/{pathway_id}/nodes/{node_number}**
Get details for a specific pathway node.

**Parameters:**
- `pathway_id` (path): Pathway ID
- `node_number` (path): Node number

**Response:**
```json
{
  "node": {
    "nodeNumber": 1,
    "title": "Understanding Your Triggers",
    "description": "In this exercise, you'll learn to identify what triggers your anxiety",
    "exerciseLink": "https://example.com/exercise1",
    "estimatedDuration": 15,
    "isCompleted": false
  },
  "pathwayInfo": {
    "title": "Managing Anxiety",
    "progress": "2/10 completed"
  }
}
```

#### **POST /wellness/pathways/{pathway_id}/nodes/{node_number}/complete**
Mark a pathway node as completed.

**Parameters:**
- `pathway_id` (path): Pathway ID
- `node_number` (path): Node number

**Response:**
```json
{
  "success": true,
  "message": "Node marked as completed",
  "nextNode": 4
}
```

#### **GET /wellness/world/posts**
Get posts from the wellness community world.

**Query Parameters:**
- `limit` (optional): Number of posts (default: 20)
- `tag` (optional): Filter by tag
- `postType` (optional): Filter by post type

**Response:**
```json
{
  "posts": [
    {
      "id": "firestore-doc-id",
      "username": "john_doe",
      "displayName": "John Doe",
      "content": "Just completed my first week of meditation! 🧘‍♂️",
      "postType": "achievement",
      "tags": ["meditation", "milestone"],
      "likesCount": 15,
      "isLiked": false,
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### **POST /wellness/world/posts**
Create a new post in the wellness world.

**Body:**
```json
{
  "content": "Just hit 30 days without smoking! 🎉",
  "postType": "achievement",
  "tags": ["smoking-cessation", "milestone"]
}
```

**Response:**
```json
{
  "success": true,
  "postId": "firestore-doc-id"
}
```

#### **POST /wellness/world/posts/{post_id}/like**
Like/unlike a post.

**Parameters:**
- `post_id` (path): Firestore document ID

**Response:**
```json
{
  "success": true,
  "isLiked": true,
  "likesCount": 16
}
```

#### **GET /wellness/community/groups**
Get available community groups.

**Query Parameters:**
- `category` (optional): Filter by category
- `myGroups` (optional): true/false - only return user's groups

**Response:**
```json
{
  "groups": [
    {
      "id": "firestore-doc-id",
      "name": "Anxiety Support",
      "description": "A safe space for people dealing with anxiety",
      "category": "mental-health",
      "memberCount": 234,
      "isMember": true,
      "isPrivate": false
    }
  ]
}
```

#### **POST /wellness/community/groups/{group_id}/join**
Join a community group.

**Parameters:**
- `group_id` (path): Firestore document ID

**Response:**
```json
{
  "success": true,
  "message": "Joined group successfully"
}
```

#### **POST /wellness/community/groups/{group_id}/leave**
Leave a community group.

**Parameters:**
- `group_id` (path): Firestore document ID

**Response:**
```json
{
  "success": true,
  "message": "Left group successfully"
}
```

#### **GET /wellness/community/groups/{group_id}/messages**
Get recent messages from a group.

**Parameters:**
- `group_id` (path): Firestore document ID
- `limit` (query, optional): Number of messages (default: 50)

**Response:**
```json
{
  "messages": [
    {
      "id": "firestore-doc-id",
      "username": "john_doe",
      "displayName": "John Doe",
      "content": "Hope everyone is having a good day!",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### **POST /wellness/community/groups/{group_id}/messages**
Send a message to a community group (alternative to WebSocket for offline scenarios).

**Parameters:**
- `group_id` (path): Firestore document ID

**Body:**
```json
{
  "content": "Thanks for all the support everyone!"
}
```

**Response:**
```json
{
  "success": true,
  "messageId": "firestore-doc-id"
}
```

---

## WebSocket Connection (Community Chat Only)

For real-time Discord-style messaging in community groups, we'll implement a single WebSocket connection:

### Community Chat WebSocket
**Endpoint:** `wss://your-api-domain.com/ws/community/{group_id}`

**Authentication:** JWT token as query parameter
- Example: `wss://api.com/ws/community/group123?token=your-jwt-token`

**Purpose:** Real-time messaging within community groups

#### Client → Server Messages

**Join Group Chat:**
```json
{
  "type": "join_group",
  "groupId": "firestore-group-id"
}
```

**Send Message:**
```json
{
  "type": "send_message",
  "groupId": "firestore-group-id", 
  "content": "Hello everyone! 👋",
  "replyTo": "optional-message-id"
}
```

**Typing Indicator:**
```json
{
  "type": "typing",
  "groupId": "firestore-group-id",
  "isTyping": true
}
```

**Leave Group:**
```json
{
  "type": "leave_group",
  "groupId": "firestore-group-id"
}
```

#### Server → Client Messages

**User Joined:**
```json
{
  "type": "user_joined",
  "groupId": "firestore-group-id",
  "user": {
    "userId": "user123",
    "username": "john_doe",
    "displayName": "John Doe"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**New Message:**
```json
{
  "type": "new_message",
  "groupId": "firestore-group-id",
  "message": {
    "id": "firestore-message-id",
    "userId": "user123",
    "username": "john_doe",
    "displayName": "John Doe",
    "content": "Hello everyone! 👋",
    "replyTo": {
      "messageId": "original-message-id",
      "content": "Welcome to the group!",
      "username": "admin"
    },
    "createdAt": "2024-01-01T00:00:00Z"
  }
}
```

**Typing Indicator:**
```json
{
  "type": "user_typing",
  "groupId": "firestore-group-id",
  "user": {
    "userId": "user123",
    "username": "john_doe",
    "displayName": "John Doe"
  },
  "isTyping": true,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**User Left:**
```json
{
  "type": "user_left",
  "groupId": "firestore-group-id",
  "userId": "user123",
  "username": "john_doe",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Online Users Count:**
```json
{
  "type": "online_count",
  "groupId": "firestore-group-id",
  "count": 12,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Connection Confirmed:**
```json
{
  "type": "connection_confirmed",
  "groupId": "firestore-group-id",
  "userId": "your-user-id",
  "message": "Connected to group chat"
}
```

**Error:**
```json
{
  "type": "error",
  "code": "INVALID_GROUP",
  "message": "Group not found or access denied",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Implementation Notes for WebSocket Chat:

1. **Message Persistence**: All messages sent via WebSocket are also saved to Firestore `groupMessages` collection
2. **Connection Management**: Track active connections per group for online count
3. **Authentication**: Verify JWT token on WebSocket connection
4. **Group Membership**: Verify user is a member of the group before allowing connection
5. **Rate Limiting**: Limit messages per user (e.g., 30 messages per minute)
6. **Reconnection**: Client should handle reconnection on disconnect

### FastAPI WebSocket Implementation Example:
```python
from fastapi import WebSocket, WebSocketDisconnect
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, group_id: str):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
    
    async def broadcast_to_group(self, group_id: str, message: dict):
        if group_id in self.active_connections:
            for connection in self.active_connections[group_id]:
                await connection.send_text(json.dumps(message))

manager = ConnectionManager()

@app.websocket("/ws/community/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: str, token: str):
    # Verify token and group membership
    user_id = verify_token(token)
    if not is_group_member(user_id, group_id):
        await websocket.close(code=4003)
        return
    
    await manager.connect(websocket, group_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # Handle different message types
            await handle_message(message, group_id, user_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id)
```

---

### File Management (Simple)

#### **POST /upload/avatar**
Upload user avatar image.

**Body:** `multipart/form-data`
- `image`: Image file (.jpg, .png, .webp)

**Response:**
```json
{
  "success": true,
  "avatarUrl": "gs://bucket/avatars/user-avatar.jpg"
}
```

---

## Authentication Middleware

All endpoints (except health checks) require a valid Supabase JWT token in the Authorization header:

```
Authorization: Bearer <supabase-jwt-token>
```

### Token Validation Flow:
1. Extract token from Authorization header
2. Verify token with Supabase (using their SDK)
3. Extract user ID from token
4. Use user ID for database operations

### FastAPI Implementation Example:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    try:
        # Verify with Supabase
        payload = jwt.decode(token.credentials, options={"verify_signature": False})
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## Error Responses (Simplified)

All API endpoints return errors in this simple format:

```json
{
  "success": false,
  "message": "Clear error message describing what went wrong",
  "code": "VALIDATION_ERROR"
}
```

### Common Error Codes
- `AUTHENTICATION_REQUIRED`: Missing or invalid auth token
- `VALIDATION_ERROR`: Request validation failed  
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `SERVER_ERROR`: Internal server error
- `PERMISSION_DENIED`: User lacks permission for resource

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (auth errors)
- `404`: Not Found
- `500`: Internal Server Error

---

## Deployment Notes (GCP Free Tier)

### Recommended GCP Services:
- **Cloud Run**: Host FastAPI backend (free tier: 2 million requests/month)
- **Cloud Firestore**: Primary database (free tier: 50K reads, 20K writes/day)
- **Cloud Storage**: File storage (free tier: 5GB)
- **Cloud Functions**: Optional for AI processing (free tier: 2 million invocations/month)

### Environment Variables:
```
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
GOOGLE_APPLICATION_CREDENTIALS=path-to-service-account-json
GCP_PROJECT_ID=your-project-id
OPENAI_API_KEY=your-openai-api-key (for AI features)
```

### FastAPI Requirements:
```
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
google-cloud-firestore==2.13.1
google-cloud-storage==2.10.0
supabase==2.0.2
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
openai==1.3.0
```

This architecture is perfect for a hackathon - **simple REST APIs + one WebSocket for real-time chat** - using Google Cloud services with Discord-style messaging!
