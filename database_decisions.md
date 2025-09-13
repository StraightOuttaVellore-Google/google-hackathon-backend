# Database Architecture Decisions - Hackathon Edition

## Overview
This document outlines the simplified database strategy for the Wellness & Study App hackathon project, focusing on simplicity and using GCP free tier services with Supabase for authentication only.

## Database Strategy (Simplified for Hackathon)

### Primary Database: Cloud Firestore (GCP)
**Rationale**: For a hackathon project requiring simplicity:
- **Free tier**: 50K reads, 20K writes, 20K deletes per day
- **NoSQL**: No complex schema setup needed
- **Real-time**: Built-in real-time updates (if needed later)
- **Easy setup**: Minimal configuration required
- **Google integration**: Perfect for Google Hackathon

### Authentication: Supabase
**Rationale**: Keep as planned since you're already using it:
- Handle user registration/login
- JWT tokens for API authentication
- No need for complex user management

### File Storage: Google Cloud Storage
**Rationale**: For hackathon simplicity:
- **Free tier**: 5GB storage
- **Audio files**: Store voice journaling recordings temporarily
- **Simple API**: Easy to integrate with FastAPI

## Data Structure Strategy (Firestore Collections)

### Collection: `users`
**Purpose**: Store user profile data (separate from Supabase auth)
```json
{
  "userId": "supabase-user-id",
  "username": "john_doe",
  "displayName": "John Doe", 
  "avatarUrl": "gs://bucket/avatar.jpg",
  "totalFishes": 0,
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

### Collection: `tasks`
**Purpose**: Eisenhower Matrix tasks
```json
{
  "id": "auto-generated-id",
  "userId": "supabase-user-id",
  "title": "Complete project proposal",
  "description": "Detailed description here",
  "quadrant": "urgent_important", // or "not_urgent_important", etc.
  "status": "pending", // "completed", "cancelled"
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

### Collection: `chatConversations`
**Purpose**: AI assistant conversations
```json
{
  "id": "auto-generated-id",
  "userId": "supabase-user-id",
  "title": "Daily Planning Chat",
  "messages": [
    {
      "role": "user",
      "content": "Help me plan my day",
      "timestamp": "2024-01-01T00:00:00Z"
    },
    {
      "role": "assistant", 
      "content": "I'd be happy to help! What are your priorities?",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ],
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

### Collection: `journalEntries`
**Purpose**: Voice journaling data
```json
{
  "id": "auto-generated-id",
  "userId": "supabase-user-id",
  "title": "Morning Reflection",
  "audioUrl": "gs://bucket/audio/recording.wav", // Optional, can be deleted after processing
  "transcript": "Today I felt really good about my progress...",
  "summary": "Positive reflection on daily progress and goals",
  "moodTags": ["happy", "motivated", "grateful"],
  "riskAssessment": "low", // "medium", "high"
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### Collection: `dailyMoods`
**Purpose**: Daily mood tracking for calendar
```json
{
  "id": "auto-generated-id",
  "userId": "supabase-user-id", 
  "date": "2024-01-01", // YYYY-MM-DD format
  "emoji": "😊",
  "summary": "Great day with high energy and motivation",
  "tags": ["productive", "happy"],
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### Collection: `pathways`
**Purpose**: Wellness pathway templates (admin managed)
```json
{
  "id": "anxiety-management-101",
  "title": "Managing Anxiety",
  "description": "A step-by-step guide to understanding and managing anxiety",
  "category": "anxiety",
  "nodes": [
    {
      "nodeNumber": 1,
      "title": "Understanding Triggers",
      "description": "Learn to identify what triggers your anxiety",
      "exerciseLink": "https://example.com/exercise1",
      "estimatedDuration": 15
    }
  ],
  "totalNodes": 10,
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### Collection: `userPathwayProgress`
**Purpose**: Track user progress in pathways
```json
{
  "id": "auto-generated-id",
  "userId": "supabase-user-id",
  "pathwayId": "anxiety-management-101", 
  "currentNode": 3,
  "completedNodes": [1, 2],
  "startedAt": "2024-01-01T00:00:00Z",
  "lastActivity": "2024-01-01T00:00:00Z"
}
```

### Collection: `posts`
**Purpose**: Community world posts (Twitter-like)
```json
{
  "id": "auto-generated-id",
  "userId": "supabase-user-id",
  "username": "john_doe", // Denormalized for performance
  "displayName": "John Doe", // Denormalized for performance
  "content": "Just completed my first week of meditation! 🧘‍♂️",
  "postType": "achievement", // "milestone", "support"
  "tags": ["meditation", "milestone"],
  "likesCount": 15,
  "likedBy": ["user1", "user2"], // Array of user IDs for simplicity
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### Collection: `communityGroups`
**Purpose**: Community chat groups
```json
{
  "id": "auto-generated-id",
  "name": "Anxiety Support",
  "description": "A safe space for anxiety support",
  "category": "mental-health",
  "memberIds": ["user1", "user2", "user3"],
  "memberCount": 3,
  "isPrivate": false,
  "createdBy": "user1",
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### Collection: `groupMessages`
**Purpose**: Community group messages (supports real-time chat via WebSocket)
```json
{
  "id": "auto-generated-id",
  "groupId": "group-id",
  "userId": "supabase-user-id",
  "username": "john_doe", // Denormalized for performance
  "displayName": "John Doe", // Denormalized for performance
  "content": "Hope everyone is having a good day!",
  "replyTo": "optional-message-id", // For threaded conversations
  "messageType": "text", // "text", "image", "system" (for join/leave notifications)
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### In-Memory Data (for WebSocket Chat)
**Purpose**: Track active connections and typing indicators (not persisted)
```javascript
// Connection Manager in FastAPI
{
  "activeConnections": {
    "group-id-1": ["websocket1", "websocket2"],
    "group-id-2": ["websocket3", "websocket4"]
  },
  "typingUsers": {
    "group-id-1": {
      "user123": "2024-01-01T00:00:30Z", // Timestamp of last typing
      "user456": "2024-01-01T00:00:25Z"
    }
  },
  "onlineUsers": {
    "group-id-1": ["user123", "user456", "user789"]
  }
}
```

## Data Flow Examples (Simplified)

### Voice Journaling Flow
1. User uploads audio → Store temporarily in Google Cloud Storage
2. Audio → AI processing in your FastAPI backend
3. AI response → Save transcript, summary, mood to Firestore `journalEntries`
4. Update daily mood → Upsert into Firestore `dailyMoods` collection

### Task Management Flow
1. User creates task → Add to Firestore `tasks` collection
2. User updates task → Update document in Firestore
3. Pomodoro completion → Increment `totalFishes` in `users` collection

### Chat Assistant Flow
1. User sends message → Append to `messages` array in `chatConversations`
2. AI processing → Generate response in FastAPI backend
3. AI response → Append to same `messages` array

### Community Features Flow
1. User posts achievement → Add to `posts` collection
2. User likes post → Add userId to `likedBy` array, increment `likesCount`
3. User joins group → Add userId to `memberIds` array in `communityGroups`
4. **Real-time Chat Flow:**
   - User connects to WebSocket → Verify group membership → Add to active connections
   - User sends message via WebSocket → Save to `groupMessages` collection + broadcast to all group members
   - Typing indicators → Broadcast to active connections only (not saved)
   - User disconnects → Remove from active connections

## Security Considerations (Simplified)

### Firestore Security Rules
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    match /tasks/{taskId} {
      allow read, write: if request.auth != null && 
        request.auth.uid == resource.data.userId;
    }
    
    match /journalEntries/{entryId} {
      allow read, write: if request.auth != null && 
        request.auth.uid == resource.data.userId;
    }
    
    // Public read for pathways, community posts
    match /pathways/{pathwayId} {
      allow read: if request.auth != null;
    }
    
    match /posts/{postId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        request.auth.uid == resource.data.userId;
    }
  }
}
```

### API Authentication
- All endpoints require valid Supabase JWT token
- Verify JWT token in FastAPI middleware
- Extract userId from token for data access

## Hackathon Implementation Strategy

### Phase 1: Core Features (Day 1)
- User profile management
- Eisenhower matrix tasks
- Basic AI chat assistant

### Phase 2: Wellness Features (Day 2)
- Voice journaling with AI processing
- Daily mood tracking
- Wellness pathways (basic version)

### Phase 3: Community Features (Day 3)
- World posts (Twitter-like)
- Community groups and messaging
- Polish and testing

## Free Tier Limits to Watch
- **Firestore**: 50K reads, 20K writes, 20K deletes per day
- **Cloud Storage**: 5GB total storage
- **No complex caching needed** - Firestore handles most performance needs
- **Simple architecture** - No Redis or complex real-time features needed
