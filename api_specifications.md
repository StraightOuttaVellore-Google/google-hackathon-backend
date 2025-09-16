# API Specifications - Unified Strategy

## Overview
This document outlines the consolidated API strategy for the Wellness & Study App, based on the principle of minimizing database calls. The primary interaction model is a single data load on startup and a single sync endpoint for saving session changes. All endpoints require authentication via Supabase JWT token.

## Base Configuration
- **Base URL**: `https://your-api-domain.com/api/v1`
- **Authentication**: Bearer token in Authorization header (`Authorization: Bearer <supabase-jwt-token>`)
- **Primary Database**: Google Cloud Firestore

---

## Session-Based Endpoints

### 1. The Startup Endpoint
This is the most critical endpoint. It's called once after login to fetch all data required to initialize the frontend application state.

#### **GET /user/startup**
- **Description**: Get all initial data for the user's session. The user ID is extracted from the JWT.
- **Response (`StartupData` object)**:
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
    "eisenhower_tasks": [
        // Array of all user's tasks from the 'tasks' collection
    ],
    "chat_conversations": [
        // List of conversation titles and IDs from 'chatConversations'
    ]
  },
  "wellness_data": {
    "daily_moods_current_month": [
        // Array of 'dailyMoods' for the current month
    ],
    "active_pathways": [
        // Array of pathways the user is enrolled in, with progress
    ],
    "recent_journals": [
        // Summary of the last 5 journal entries
    ]
  },
  "community_data": {
      "user_groups": [
          // List of community groups the user is a member of
      ]
  }
}
```

### 2. The Sync Endpoint
This endpoint is used by the frontend to persist all changes made during a user session back to the database in a single batch operation.

#### **POST /user/sync**
- **Description**: Receives the updated state from the client and updates the relevant Firestore collections.
- **When to Call**: Periodically (e.g., every 2-3 minutes) and when the user navigates away from the page (`beforeunload` event).
- **Request Body**: The body mirrors the `StartupData` structure, containing the updated arrays of tasks, moods, etc.
- **Response**:
```json
{
  "success": true,
  "message": "Data synced successfully."
}
```
---

## Specialized Endpoints (Transactional & File Uploads)
These endpoints are for operations that don't fit the sync model and require immediate, specific server responses.

#### **POST /wellness/voice-journal**
- **Description**: Process voice journaling (upload audio, get AI analysis).
- **Body**: `multipart/form-data` with `audio` file and optional `title`.
- **Reason**: Handles file uploads and immediate AI processing.
- **Response**:
```json
{
  "success": true,
  "entryId": "firestore-doc-id",
  "transcript": "...",
  "summary": "...",
  "moodTags": ["happy", "motivated"],
  "riskAssessment": "low"
}
```

#### **POST /study/chat/message**
- **Description**: Send a message to the AI assistant in an existing conversation.
- **Body**: `{ "conversationId": "...", "content": "..." }`
- **Reason**: Interactive chat requires an immediate response from the AI model.
- **Response**:
```json
{
  "success": true,
  "aiResponse": "Based on your current tasks, I recommend..."
}
```

#### **GET /wellness/world/posts**
- **Description**: Get posts from the wellness community world.
- **Reason**: Fetches fresh, public data not tied to a single user's session state.
- **Response**:
```json
{
  "posts": [ /* Array of post objects */ ]
}
```
*(Accompanying `POST /wellness/world/posts` and `POST /wellness/world/posts/{post_id}/like` endpoints are also required for this feature).*

---

## Real-Time WebSocket Endpoint

#### **`wss://your-api-domain.com/ws/community/{group_id}`**
- **Description**: Provides real-time, bidirectional messaging for community groups.
- **Authentication**: JWT token passed as a query parameter.
- **Reason**: The only feature requiring true real-time communication.
- **Messages**: JSON-based messages for joining, leaving, sending messages, and typing indicators as previously specified.

---

## Error Responses
All API endpoints should return errors in a consistent format:
```json
{
  "success": false,
  "message": "A clear error message describing what went wrong.",
  "code": "ERROR_CODE"
}
```
