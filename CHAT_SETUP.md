# Chat Backend Setup Guide

## Overview

This guide covers the setup and configuration of the chat feature that has been integrated into the FastAPI backend.

## New Database Models

The following models have been added to `model.py`:

### ChatServer
- Represents a chat server (like Discord servers)
- Contains name, icon, creator reference
- Each server can have multiple channels

### ChatChannel
- Represents channels within a server
- Can be TEXT or VOICE type
- Ordered by position field

### ChatMessage
- Stores all chat messages
- Links to server, channel, and user
- Timestamps for message ordering

### ServerMembership
- Manages user access to servers
- Supports roles: ADMIN, MODERATOR, MEMBER
- Enforces server permissions

## Installation Steps

### 1. Database Migration

The tables will be automatically created when you start the FastAPI application:

```bash
uvicorn main:app --reload
```

SQLModel will detect the new models and create the tables in PostgreSQL.

### 2. Seed Initial Data

Run the seed script to create sample servers:

```bash
python seed_chat_data.py
```

This creates:
- 3 sample servers
- Text and voice channels for each server
- Adds all existing users as members

### 3. Verify Tables

Connect to your PostgreSQL database and verify:

```sql
-- Check if tables exist
\dt

-- View servers
SELECT * FROM chatserver;

-- View channels
SELECT * FROM chatchannel;

-- View memberships
SELECT * FROM servermembership;
```

## API Endpoints

All endpoints are prefixed with `/chat`

### Server Management

```python
GET    /chat/servers                    # Get user's servers
POST   /chat/servers                    # Create new server
GET    /chat/servers/{id}/channels      # Get server channels
POST   /chat/servers/{id}/channels      # Create channel (admin)
DELETE /chat/servers/{id}               # Delete server (admin)
```

### Channel Operations

```python
GET    /chat/servers/{sid}/channels/{cid}/messages  # Get messages
POST   /chat/servers/{sid}/channels/{cid}/messages  # Send message (via WS)
```

### Member Management

```python
POST   /chat/servers/{id}/members       # Add member (admin)
DELETE /chat/servers/{id}/members/{uid} # Remove member (admin)
```

### WebSocket

```python
WS     /chat/ws?token={jwt_token}       # Real-time connection
```

## Authentication

All endpoints use the existing JWT authentication system:

```python
from utils import TokenDep

@router.get("/endpoint")
async def endpoint(token: TokenDep, session: SessionDep):
    user_id = uuid.UUID(token.user_id)
    # ... your code
```

The WebSocket endpoint authenticates via query parameter:

```python
ws://localhost:8000/chat/ws?token=<jwt_token>
```

## Permission System

### Server Access
- Users can only access servers they are members of
- Membership is managed via ServerMembership table

### Roles
- **ADMIN**: Can create channels, manage members, delete server
- **MODERATOR**: Can manage messages and members
- **MEMBER**: Can send messages, view channels

### Helper Functions

```python
# Check if user has access to server
user_has_server_access(session, user_id, server_id)

# Get user's role in server
get_user_role_in_server(session, user_id, server_id)

# Get all server members
get_server_members(session, server_id)

# Check if user can send messages
user_can_send_message(session, user_id, server_id, channel_id)
```

## WebSocket Connection Manager

The `ConnectionManager` class handles WebSocket connections:

```python
from routers.chat_manager import manager

# Register connection
await manager.connect(user_id, websocket)

# Send to specific user
await manager.send_personal(user_id, message_dict)

# Broadcast to channel
await manager.broadcast_to_channel(
    server_id,
    channel_id,
    message_dict,
    allowed_users_set
)

# Disconnect user
manager.disconnect(user_id)
```

## Event Types

### Client → Server

```json
{
  "type": "send_message",
  "serverId": "uuid",
  "channelId": "uuid",
  "text": "message text"
}

{
  "type": "typing_start",
  "serverId": "uuid",
  "channelId": "uuid"
}

{
  "type": "typing_stop",
  "serverId": "uuid",
  "channelId": "uuid"
}
```

### Server → Client

```json
{
  "type": "new_message",
  "id": "uuid",
  "user": "username",
  "text": "message",
  "timestamp": "12:30 PM",
  "serverId": "uuid",
  "channelId": "uuid"
}

{
  "type": "typing_start",
  "username": "user",
  "serverId": "uuid",
  "channelId": "uuid"
}

{
  "type": "error",
  "message": "error description"
}
```

## Testing

### Manual Testing

1. Start the backend:
```bash
uvicorn main:app --reload
```

2. Test REST endpoints:
```bash
# Get servers (replace with valid token)
curl -H "Authorization: Bearer <token>" http://localhost:8000/chat/servers

# Get channels
curl -H "Authorization: Bearer <token>" http://localhost:8000/chat/servers/<server_id>/channels
```

3. Test WebSocket:
```javascript
// In browser console
const token = 'your-jwt-token'
const ws = new WebSocket(`ws://localhost:8000/chat/ws?token=${token}`)

ws.onmessage = (e) => console.log(JSON.parse(e.data))

// Send message
ws.send(JSON.stringify({
  type: 'send_message',
  serverId: 'server-uuid',
  channelId: 'channel-uuid',
  text: 'Hello!'
}))
```

### With Multiple Users

1. Open multiple browser tabs
2. Login as different users
3. Connect to same server/channel
4. Send messages and verify real-time delivery

## Monitoring

### Active Connections

```python
from routers.chat_manager import manager

# Check active connections
print(f"Active connections: {len(manager.active_connections)}")
print(f"Users: {list(manager.active_connections.keys())}")
```

### Message Stats

```sql
-- Total messages
SELECT COUNT(*) FROM chatmessage;

-- Messages per channel
SELECT c.name, COUNT(m.id) as message_count
FROM chatchannel c
LEFT JOIN chatmessage m ON c.id = m.channel_id
GROUP BY c.name;

-- Active users (messages in last 24 hours)
SELECT DISTINCT u.username
FROM users u
JOIN chatmessage m ON u.user_id = m.user_id
WHERE m.created_at > NOW() - INTERVAL '24 hours';
```

## Performance Considerations

### Database Indexes
The following indexes are automatically created:
- `chatserver.name` - Fast server lookups
- `chatchannel.server_id` - Fast channel queries
- `chatmessage.server_id, channel_id` - Fast message retrieval
- `servermembership.server_id, user_id` - Fast permission checks

### Message Pagination
Always use limit/offset for message queries:
```python
GET /chat/servers/{sid}/channels/{cid}/messages?limit=50&offset=0
```

### WebSocket Cleanup
Connections are automatically cleaned up on disconnect or error.

## Troubleshooting

### Tables Not Created
- Check database connection in `.env`
- Verify `create_db_and_tables()` is called in `main.py`
- Check for SQLAlchemy errors in logs

### Permission Errors
- Verify user has ServerMembership record
- Check role assignment
- Ensure server_id and channel_id are valid UUIDs

### WebSocket Issues
- Verify token is valid and not expired
- Check CORS configuration in `main.py`
- Monitor server logs for WebSocket errors

### Message Not Broadcasting
- Check if all users are members of the server
- Verify `broadcast_to_channel` receives correct user IDs
- Check WebSocket connection status

## Security Considerations

1. **Token Validation**: All endpoints validate JWT tokens
2. **Permission Checks**: Server access verified on every action
3. **SQL Injection**: Prevented by SQLModel parameterization
4. **XSS**: Frontend should sanitize message display
5. **Rate Limiting**: Consider adding to prevent spam

## Environment Variables

Required in `.env`:

```env
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
DB_NAME=yourdb
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Future Enhancements

Potential features to add:

1. **Direct Messages**: One-on-one chat between users
2. **File Uploads**: Share images, files in channels
3. **Reactions**: React to messages with emojis
4. **Threads**: Reply threads for messages
5. **Message Search**: Full-text search across messages
6. **User Status**: Online/offline/away indicators
7. **Notifications**: Push notifications for mentions
8. **Message Editing**: Edit/delete sent messages
9. **Channel Categories**: Organize channels in groups
10. **Server Invites**: Invite links for joining servers

## Support

For issues or questions:
1. Check server logs for errors
2. Verify database connectivity
3. Test with sample data from seed script
4. Review API documentation above
