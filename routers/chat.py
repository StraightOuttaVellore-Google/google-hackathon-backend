"""
Chat Router - Firebase Version
Discord-style chat with servers, channels, and real-time messaging using Firestore.

MIGRATED TO FIREBASE - All PostgreSQL dependencies removed.
"""

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    HTTPException,
    status,
)
from typing import List, Set, Dict, Optional
import uuid
from datetime import datetime
import json

from firebase_db import get_firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP, ArrayUnion
from utils import TokenDep, verify_access_token
from model import (
    CreateServerData,
    CreateChannelData,
    SendMessageData,
    AddMemberData,
    ServerResponse,
    ChannelResponse,
    MessageResponse,
)
from routers.chat_manager import manager

router = APIRouter(prefix="/chat", tags=["chat"])


# ==================== FIREBASE HELPER FUNCTIONS ====================

def user_has_server_access(db, user_id: str, server_id: str) -> bool:
    """Check if a user has access to a specific server"""
    try:
        # Check if user is in server's member_ids array
        server_ref = db.collection('chatServers').document(server_id)
        server_doc = server_ref.get()
        
        if not server_doc.exists:
            return False
        
        server_data = server_doc.to_dict()
        member_ids = server_data.get('member_ids', [])
        return user_id in member_ids
    except Exception as e:
        print(f"Error checking server access: {e}")
        return False


def get_user_role_in_server(db, user_id: str, server_id: str) -> Optional[str]:
    """Get user's role in a server"""
    try:
        memberships_ref = db.collection('serverMemberships')
        query = memberships_ref.where('server_id', '==', server_id)\
                              .where('user_id', '==', user_id)\
                              .limit(1)
        
        docs = list(query.stream())
        if docs:
            return docs[0].to_dict().get('role', 'member')
        return None
    except Exception as e:
        print(f"Error getting user role: {e}")
        return None


def get_server_members(db, server_id: str) -> Set[str]:
    """Get all user IDs who are members of a server"""
    try:
        server_ref = db.collection('chatServers').document(server_id)
        server_doc = server_ref.get()
        
        if not server_doc.exists:
            return set()
        
        server_data = server_doc.to_dict()
        return set(server_data.get('member_ids', []))
    except Exception as e:
        print(f"Error getting server members: {e}")
        return set()


def get_user_accessible_servers(db, user_id: str) -> List[dict]:
    """Get all servers that a user has access to"""
    try:
        # Query servers where user is in member_ids array
        servers_ref = db.collection('chatServers')
        query = servers_ref.where('member_ids', 'array_contains', user_id)
        
        servers = []
        for doc in query.stream():
            data = doc.to_dict()
            
            # Handle timestamp conversion
            created_at = data.get('created_at')
            if hasattr(created_at, 'isoformat'):
                created_at_str = created_at.isoformat()
            elif hasattr(created_at, 'timestamp'):
                created_at_str = datetime.fromtimestamp(created_at.timestamp()).isoformat()
            else:
                created_at_str = datetime.utcnow().isoformat()
            
            servers.append({
                "id": doc.id,
                "name": data.get('name', ''),
                "icon": data.get('icon', ''),
                "description": data.get('description', ''),
                "created_by": data.get('created_by', ''),
                "created_at": created_at_str,
            })
        
        return servers
    except Exception as e:
        print(f"Error getting accessible servers: {e}")
        return []


def user_can_send_message(db, user_id: str, server_id: str, channel_id: str) -> bool:
    """Check if a user can send messages to a specific channel"""
    return user_has_server_access(db, user_id, server_id)


# ==================== REST ENDPOINTS ====================

@router.get("/servers")
async def get_servers(token: TokenDep):
    """Get all servers accessible to the current user"""
    try:
        db = get_firestore()
        user_id = str(token.user_id)
        servers = get_user_accessible_servers(db, user_id)
        return {"servers": servers}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving servers: {str(e)}"
        )


@router.post("/servers")
async def create_server(data: CreateServerData, token: TokenDep):
    """Create a new server"""
    try:
        db = get_firestore()
        user_id = str(token.user_id)
        
        # Check if server name already exists
        servers_ref = db.collection('chatServers')
        existing_query = servers_ref.where('name', '==', data.name).limit(1)
        existing = list(existing_query.stream())
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Server name already exists. Please choose a different name.",
            )
        
        # Create server document
        server_id = str(uuid.uuid4())
        server_ref = servers_ref.document(server_id)
        
        server_data = {
            "name": data.name,
            "icon": data.icon,
            "description": getattr(data, 'description', ''),
            "created_by": user_id,
            "member_ids": [user_id],  # Creator is auto-member
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
        }
        
        server_ref.set(server_data)
        
        # Create membership record
        membership_id = str(uuid.uuid4())
        memberships_ref = db.collection('serverMemberships')
        memberships_ref.document(membership_id).set({
            "server_id": server_id,
            "user_id": user_id,
            "role": "admin",
            "joined_at": SERVER_TIMESTAMP,
        })
        
        # Create default general channel
        channels_ref = server_ref.collection('channels')
        general_channel_id = str(uuid.uuid4())
        channels_ref.document(general_channel_id).set({
            "name": "general",
            "type": "text",
            "position": 0,
            "created_at": SERVER_TIMESTAMP,
        })
        
        return {
            "id": server_id,
            "name": data.name,
            "icon": data.icon,
            "created_by": user_id,
            "created_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating server: {str(e)}"
        )


@router.post("/servers/{server_id}/join")
async def join_server(server_id: str, token: TokenDep):
    """Join an existing server using server ID"""
    try:
        db = get_firestore()
        user_id = str(token.user_id)
        
        # Check if server exists
        server_ref = db.collection('chatServers').document(server_id)
        server_doc = server_ref.get()
        
        if not server_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found"
            )
        
        server_data = server_doc.to_dict()
        
        # Check if user is already a member
        if user_id in server_data.get('member_ids', []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member of this server",
            )
        
        # Add user to server's member_ids
        server_ref.update({
            "member_ids": ArrayUnion([user_id])
        })
        
        # Create membership record
        membership_id = str(uuid.uuid4())
        memberships_ref = db.collection('serverMemberships')
        memberships_ref.document(membership_id).set({
            "server_id": server_id,
            "user_id": user_id,
            "role": "member",
            "joined_at": SERVER_TIMESTAMP,
        })
        
        return {
            "message": "Successfully joined server",
            "server_id": server_id,
            "server_name": server_data.get('name', ''),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error joining server: {str(e)}"
        )


@router.get("/servers/{server_id}/channels")
async def get_server_channels(server_id: str, token: TokenDep):
    """Get all channels in a server"""
    try:
        db = get_firestore()
        user_id = str(token.user_id)
        
        # Check access
        if not user_has_server_access(db, user_id, server_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this server",
            )
        
        # Get channels from subcollection
        server_ref = db.collection('chatServers').document(server_id)
        channels_ref = server_ref.collection('channels')
        
        # Get all channels
        channels_docs = list(channels_ref.stream())
        
        # Sort by position in Python
        channels_list = []
        for doc in channels_docs:
            data = doc.to_dict()
            channels_list.append({
                "id": doc.id,
                "server_id": server_id,
                "name": data.get('name', ''),
                "type": data.get('type', 'text'),
                "position": data.get('position', 0),
            })
        
        channels_list.sort(key=lambda x: x['position'])
        
        return {"channels": channels_list}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving channels: {str(e)}"
        )


@router.post("/servers/{server_id}/channels")
async def create_channel(server_id: str, data: CreateChannelData, token: TokenDep):
    """Create a new channel (admin only)"""
    try:
        db = get_firestore()
        user_id = str(token.user_id)
        
        # Check if user is admin
        role = get_user_role_in_server(db, user_id, server_id)
        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create channels",
            )
        
        # Get existing channels to determine next position
        server_ref = db.collection('chatServers').document(server_id)
        channels_ref = server_ref.collection('channels')
        
        all_channels = list(channels_ref.stream())
        max_position = max([doc.to_dict().get('position', -1) for doc in all_channels]) if all_channels else -1
        next_position = max_position + 1
        
        # Create channel
        channel_id = str(uuid.uuid4())
        channel_data = {
            "name": data.name,
            "type": data.type,
            "position": next_position,
            "created_at": SERVER_TIMESTAMP,
        }
        
        channels_ref.document(channel_id).set(channel_data)
        
        return {
            "id": channel_id,
            "server_id": server_id,
            "name": data.name,
            "type": data.type,
            "position": next_position,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating channel: {str(e)}"
        )


@router.get("/servers/{server_id}/channels/{channel_id}/messages")
async def get_channel_messages(
    server_id: str,
    channel_id: str,
    token: TokenDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get message history for a channel"""
    try:
        db = get_firestore()
        user_id = str(token.user_id)
        
        # Check access
        if not user_has_server_access(db, user_id, server_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this server",
            )
        
        # Get messages from server's messages subcollection
        server_ref = db.collection('chatServers').document(server_id)
        messages_ref = server_ref.collection('messages')
        
        # Query messages for this channel (filter in Python to avoid index)
        all_messages = list(messages_ref.stream())
        
        # Filter by channel_id
        channel_messages = [
            doc for doc in all_messages 
            if doc.to_dict().get('channel_id') == channel_id
        ]
        
        # Sort by created_at (newest first for pagination, then reverse)
        channel_messages.sort(
            key=lambda x: x.to_dict().get('created_at', datetime.min),
            reverse=True
        )
        
        # Apply pagination
        paginated = channel_messages[offset:offset+limit]
        
        # Build response (reverse to chronological order)
        messages = []
        for doc in reversed(paginated):
            data = doc.to_dict()
            
            # Get username from user_id
            user_id_from_msg = data.get('user_id', '')
            username = data.get('username', user_id_from_msg)  # Fallback to user_id if no username
            
            # Handle timestamp
            created_at = data.get('created_at')
            if hasattr(created_at, 'strftime'):
                timestamp_str = created_at.strftime("%I:%M %p")
            elif hasattr(created_at, 'timestamp'):
                timestamp_str = datetime.fromtimestamp(created_at.timestamp()).strftime("%I:%M %p")
            else:
                timestamp_str = datetime.utcnow().strftime("%I:%M %p")
            
            messages.append({
                "id": doc.id,
                "user": username,
                "text": data.get('text', ''),
                "timestamp": timestamp_str,
                "server_id": server_id,
                "channel_id": channel_id,
            })
        
        return {"messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving messages: {str(e)}"
        )


# ==================== WEBSOCKET ENDPOINT ====================

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time chat"""
    # Authenticate user from token
    try:
        token_data = verify_access_token(token)
        user_id = str(token_data.user_id)
        username = token_data.username
    except Exception as e:
        print(f"WebSocket authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Connect user
    await manager.connect(user_id, websocket)
    
    # Get Firestore connection
    db = get_firestore()
    
    # Send initial connection confirmation
    await manager.send_personal(
        user_id,
        {
            "type": "connected",
            "message": "Connected to chat server",
            "user_id": user_id,
            "username": username,
        },
    )
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            event_type = message_data.get("type")
            
            if event_type == "send_message":
                # Extract data
                server_id = message_data.get("serverId")
                channel_id = message_data.get("channelId")
                text = message_data.get("text", "").strip()
                
                if not text:
                    continue
                
                # Check permissions
                if not user_can_send_message(db, user_id, server_id, channel_id):
                    await manager.send_personal(
                        user_id,
                        {
                            "type": "error",
                            "message": "You do not have permission to send messages in this channel",
                        },
                    )
                    continue
                
                # Save message to Firestore
                server_ref = db.collection('chatServers').document(server_id)
                messages_ref = server_ref.collection('messages')
                
                message_id = str(uuid.uuid4())
                message_doc = {
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "username": username,  # Store username for easier retrieval
                    "text": text,
                    "created_at": SERVER_TIMESTAMP,
                }
                
                messages_ref.document(message_id).set(message_doc)
                
                # Prepare broadcast message
                broadcast_data = {
                    "type": "new_message",
                    "id": message_id,
                    "user": username,
                    "text": text,
                    "timestamp": datetime.utcnow().strftime("%I:%M %p"),
                    "serverId": server_id,
                    "channelId": channel_id,
                }
                
                # Broadcast to all server members
                allowed_users = get_server_members(db, server_id)
                await manager.broadcast_to_channel(
                    server_id, channel_id, broadcast_data, allowed_users
                )
            
            elif event_type == "typing_start":
                server_id = message_data.get("serverId")
                channel_id = message_data.get("channelId")
                channel_key = f"{server_id}-{channel_id}"
                
                manager.add_typing_user(channel_key, username)
                
                # Broadcast typing indicator
                allowed_users = get_server_members(db, server_id)
                await manager.broadcast_to_channel(
                    server_id,
                    channel_id,
                    {
                        "type": "typing_start",
                        "username": username,
                        "serverId": server_id,
                        "channelId": channel_id,
                    },
                    allowed_users,
                )
            
            elif event_type == "typing_stop":
                server_id = message_data.get("serverId")
                channel_id = message_data.get("channelId")
                channel_key = f"{server_id}-{channel_id}"
                
                manager.remove_typing_user(channel_key, username)
                
                # Broadcast typing stop
                allowed_users = get_server_members(db, server_id)
                await manager.broadcast_to_channel(
                    server_id,
                    channel_id,
                    {
                        "type": "typing_stop",
                        "username": username,
                        "serverId": server_id,
                        "channelId": channel_id,
                    },
                    allowed_users,
                )
            
            elif event_type == "get_servers":
                # Send user's accessible servers
                servers = get_user_accessible_servers(db, user_id)
                await manager.send_personal(
                    user_id,
                    {
                        "type": "servers_data",
                        "servers": {server["id"]: server for server in servers},
                    },
                )
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f"User {username} disconnected")
    except Exception as e:
        print(f"WebSocket error for user {username}: {e}")
        import traceback
        traceback.print_exc()
        manager.disconnect(user_id)
