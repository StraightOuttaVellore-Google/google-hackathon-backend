from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    HTTPException,
    status,
    Response,
)
from sqlmodel import select, func
from typing import List, Set
import uuid
from datetime import datetime
import json

from db import SessionDep
from utils import TokenDep, verify_access_token
from model import (
    ChatServer,
    ChatChannel,
    ChatMessage,
    ServerMembership,
    CreateServerData,
    CreateChannelData,
    SendMessageData,
    AddMemberData,
    ServerResponse,
    ChannelResponse,
    MessageResponse,
    Users,
    ServerRole,
    ChannelType,
)
from routers.chat_manager import manager

router = APIRouter(prefix="/chat", tags=["chat"])


# Helper Functions
def user_has_server_access(
    session: SessionDep, user_id: uuid.UUID, server_id: uuid.UUID
) -> bool:
    """Check if a user has access to a specific server"""
    statement = select(ServerMembership).where(
        ServerMembership.user_id == user_id, ServerMembership.server_id == server_id
    )
    membership = session.exec(statement).first()
    return membership is not None


def get_user_role_in_server(
    session: SessionDep, user_id: uuid.UUID, server_id: uuid.UUID
) -> ServerRole | None:
    """Get user's role in a server"""
    statement = select(ServerMembership).where(
        ServerMembership.user_id == user_id, ServerMembership.server_id == server_id
    )
    membership = session.exec(statement).first()
    return membership.role if membership else None


def get_server_members(session: SessionDep, server_id: uuid.UUID) -> Set[str]:
    """Get all user IDs who are members of a server"""
    statement = select(ServerMembership.user_id).where(
        ServerMembership.server_id == server_id
    )
    members = session.exec(statement).all()
    return {str(member) for member in members}


def get_user_accessible_servers(session: SessionDep, user_id: uuid.UUID) -> List[dict]:
    """Get all servers that a user has access to"""
    statement = (
        select(ChatServer)
        .join(ServerMembership)
        .where(ServerMembership.user_id == user_id)
    )
    servers = session.exec(statement).all()

    return [
        {
            "id": str(server.id),
            "name": server.name,
            "icon": server.icon,
            "created_by": str(user_id),
            "created_at": server.created_at.isoformat(),
        }
        for server in servers
    ]


def user_can_send_message(
    session: SessionDep, user_id: uuid.UUID, server_id: uuid.UUID, channel_id: uuid.UUID
) -> bool:
    """Check if a user can send messages to a specific channel"""
    # For now, just check server access
    # Can be extended to check channel-specific permissions
    return user_has_server_access(session, user_id, server_id)


# REST Endpoints


@router.get("/servers", response_model=List[ServerResponse])
async def get_servers(token: TokenDep, session: SessionDep):
    """Get all servers accessible to the current user"""
    user_id = uuid.UUID(token.user_id)
    servers = get_user_accessible_servers(session, user_id)
    return servers


@router.post("/servers", response_model=ServerResponse)
async def create_server(data: CreateServerData, token: TokenDep, session: SessionDep):
    """Create a new server"""
    user_id = uuid.UUID(token.user_id)

    # Create server
    server = ChatServer(name=data.name, icon=data.icon, created_by=user_id)
    session.add(server)
    session.commit()
    session.refresh(server)

    # Add creator as admin
    membership = ServerMembership(
        server_id=server.id, user_id=user_id, role=ServerRole.ADMIN
    )
    session.add(membership)

    # Create default general channel
    general_channel = ChatChannel(
        server_id=server.id, name="general", type=ChannelType.TEXT, position=0
    )
    session.add(general_channel)
    session.commit()

    return ServerResponse(
        id=str(server.id),
        name=data.name,
        icon=data.icon,
        created_by=str(user_id),
        created_at=server.created_at,
    )


@router.get("/servers/{server_id}/channels", response_model=List[ChannelResponse])
async def get_server_channels(server_id: str, token: TokenDep, session: SessionDep):
    """Get all channels in a server"""
    user_id = uuid.UUID(token.user_id)
    server_uuid = uuid.UUID(server_id)

    # Check access
    if not user_has_server_access(session, user_id, server_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this server",
        )

    statement = (
        select(ChatChannel)
        .where(ChatChannel.server_id == server_uuid)
        .order_by(ChatChannel.position)
    )

    channels = session.exec(statement).all()

    return [
        {
            "id": str(channel.id),
            "server_id": str(channel.server_id),
            "name": channel.name,
            "type": channel.type,
            "position": channel.position,
        }
        for channel in channels
    ]


@router.post("/servers/{server_id}/channels", response_model=ChannelResponse)
async def create_channel(
    server_id: str, data: CreateChannelData, token: TokenDep, session: SessionDep
):
    """Create a new channel (admin only)"""
    user_id = uuid.UUID(token.user_id)
    server_uuid = uuid.UUID(server_id)
    role = get_user_role_in_server(session, user_id, server_uuid)
    if role != ServerRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create channels",
        )

    channel_name = session.exec(
        select(ChatChannel.name).where(ChatChannel.name == data.name)
    )
    if channel_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Channel Name already present in the Server",
        )

    max_position = session.exec(
        select(func.max(ChatChannel.position)).where(ChatChannel.server_id == server_id)
    ).first()

    if max_position is None:
        next_position = 0
    else:
        next_position = max_position + 1

    channel = ChatChannel(
        server_id=server_uuid, name=data.name, type=data.type, position=next_position
    )
    session.add(channel)
    session.commit()
    session.refresh(channel)

    return {
        "id": str(channel.id),
        "server_id": str(channel.server_id),
        "name": channel.name,
        "type": channel.type,
        "position": channel.position,
    }


@router.get(
    "/servers/{server_id}/channels/{channel_id}/messages",
    response_model=List[MessageResponse],
)
async def get_channel_messages(
    server_id: str,
    channel_id: str,
    token: TokenDep,
    session: SessionDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get message history for a channel"""
    user_id = uuid.UUID(token.user_id)
    server_uuid = uuid.UUID(server_id)
    channel_uuid = uuid.UUID(channel_id)

    # Check access
    if not user_has_server_access(session, user_id, server_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this server",
        )

    statement = (
        select(ChatMessage, Users.username)
        .join(Users, ChatMessage.user_id == Users.user_id)
        .where(
            ChatMessage.server_id == server_uuid, ChatMessage.channel_id == channel_uuid
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    results = session.exec(statement).all()

    # Reverse to get chronological order
    messages = [
        {
            "id": str(message.id),
            "user": username,
            "text": message.text,
            "timestamp": message.created_at.strftime("%I:%M %p"),
            "server_id": str(message.server_id),
            "channel_id": str(message.channel_id),
        }
        for message, username in reversed(results)
    ]

    return messages


@router.post("/servers/{server_id}/members")
async def add_server_member(
    server_id: str, data: AddMemberData, token: TokenDep, session: SessionDep
):
    """Add a member to a server (admin only)"""
    user_id = uuid.UUID(token.user_id)
    server_uuid = uuid.UUID(server_id)
    new_user_id = uuid.UUID(data.user_id)

    # Check if requester is admin
    role = get_user_role_in_server(session, user_id, server_uuid)
    if role != ServerRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can add members"
        )

    # Check if user already exists
    existing = session.exec(
        select(ServerMembership).where(
            ServerMembership.server_id == server_uuid,
            ServerMembership.user_id == new_user_id,
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member"
        )

    # Add member
    membership = ServerMembership(
        server_id=server_uuid, user_id=new_user_id, role=data.role
    )
    session.add(membership)
    session.commit()

    return {"message": "Member added successfully"}


@router.delete("/servers/{server_id}/members/{member_user_id}")
async def remove_server_member(
    server_id: str, member_user_id: str, token: TokenDep, session: SessionDep
):
    """Remove a member from a server (admin only)"""
    user_id = uuid.UUID(token.user_id)
    server_uuid = uuid.UUID(server_id)
    member_uuid = uuid.UUID(member_user_id)

    # Check if requester is admin
    role = get_user_role_in_server(session, user_id, server_uuid)
    if role != ServerRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove members",
        )

    # Find and delete membership
    statement = select(ServerMembership).where(
        ServerMembership.server_id == server_uuid,
        ServerMembership.user_id == member_uuid,
    )
    membership = session.exec(statement).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    session.delete(membership)
    session.commit()

    return {"message": "Member removed successfully"}


# WebSocket Endpoint


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time chat"""
    from db import engine
    from sqlmodel import Session

    # Authenticate user from token
    try:
        token_data = verify_access_token(token)
        user_id = token_data.user_id
        username = token_data.username
    except Exception as e:
        print(f"WebSocket authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Connect user
    await manager.connect(user_id, websocket)

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
            print(message_data)
            event_type = message_data.get("type")

            with Session(engine) as session:
                if event_type == "send_message":
                    # Extract data
                    server_id = uuid.UUID(message_data.get("serverId"))
                    channel_id = uuid.UUID(message_data.get("channelId"))
                    text = message_data.get("text", "").strip()

                    if not text:
                        continue

                    # Check permissions
                    user_uuid = uuid.UUID(user_id)
                    if not user_can_send_message(
                        session, user_uuid, server_id, channel_id
                    ):
                        await manager.send_personal(
                            user_id,
                            {
                                "type": "error",
                                "message": "You do not have permission to send messages in this channel",
                            },
                        )
                        continue

                    # Save message to database
                    chat_message = ChatMessage(
                        server_id=server_id,
                        channel_id=channel_id,
                        user_id=user_uuid,
                        text=text,
                    )
                    session.add(chat_message)
                    session.commit()
                    session.refresh(chat_message)

                    # Prepare broadcast message
                    broadcast_data = {
                        "type": "new_message",
                        "id": str(chat_message.id),
                        "user": username,
                        "text": text,
                        "timestamp": chat_message.created_at.strftime("%I:%M %p"),
                        "serverId": str(server_id),
                        "channelId": str(channel_id),
                    }

                    # Broadcast to all server members
                    allowed_users = get_server_members(session, server_id)
                    await manager.broadcast_to_channel(
                        str(server_id), str(channel_id), broadcast_data, allowed_users
                    )

                elif event_type == "typing_start":
                    server_id = message_data.get("serverId")
                    channel_id = message_data.get("channelId")
                    channel_key = f"{server_id}-{channel_id}"

                    manager.add_typing_user(channel_key, username)

                    # Broadcast typing indicator
                    server_uuid = uuid.UUID(server_id)
                    allowed_users = get_server_members(session, server_uuid)
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
                    server_uuid = uuid.UUID(server_id)
                    allowed_users = get_server_members(session, server_uuid)
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
                    user_uuid = uuid.UUID(user_id)
                    servers = get_user_accessible_servers(session, user_uuid)
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
        manager.disconnect(user_id)
