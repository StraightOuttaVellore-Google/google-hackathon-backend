from fastapi import WebSocket
from typing import Dict, Set
import uuid
import json
from datetime import datetime


class ConnectionManager:
    def __init__(self):
        # Track active WebSocket connections: {user_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # Track which users are in which channels: {channel_key: Set[user_id]}
        self.channel_users: Dict[str, Set[str]] = {}

        # Track typing users per channel: {channel_key: Set[username]}
        self.typing_users: Dict[str, Set[str]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Register a new WebSocket connection for a user"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(
            f"User {user_id} connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, user_id: str):
        """Remove a user's WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(
                f"User {user_id} disconnected. Total connections: {len(self.active_connections)}"
            )

        # Remove user from all channels
        for channel_key in list(self.channel_users.keys()):
            if user_id in self.channel_users[channel_key]:
                self.channel_users[channel_key].remove(user_id)
                if not self.channel_users[channel_key]:
                    del self.channel_users[channel_key]

        # Remove user from typing indicators
        for channel_key in list(self.typing_users.keys()):
            if user_id in self.typing_users[channel_key]:
                self.typing_users[channel_key].remove(user_id)
                if not self.typing_users[channel_key]:
                    del self.typing_users[channel_key]

    async def send_personal(self, user_id: str, message: dict):
        """Send a message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast_to_channel(
        self, server_id: str, channel_id: str, message: dict, allowed_users: Set[str]
    ):
        """
        Broadcast a message to all users in a channel who have permission

        Args:
            server_id: The server ID
            channel_id: The channel ID
            message: The message to send
            allowed_users: Set of user_ids who are members of the server
        """
        # Send to all connected users who are members of the server
        disconnected_users = []
        for user_id, websocket in self.active_connections.items():
            if user_id in allowed_users:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    print(f"Error broadcasting to user {user_id}: {e}")
                    disconnected_users.append(user_id)

        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)

    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected users"""
        disconnected_users = []
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to user {user_id}: {e}")
                disconnected_users.append(user_id)

        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)

    def add_typing_user(self, channel_key: str, username: str):
        """Add a user to the typing indicator for a channel"""
        if channel_key not in self.typing_users:
            self.typing_users[channel_key] = set()
        self.typing_users[channel_key].add(username)

    def remove_typing_user(self, channel_key: str, username: str):
        """Remove a user from the typing indicator for a channel"""
        if channel_key in self.typing_users:
            self.typing_users[channel_key].discard(username)
            if not self.typing_users[channel_key]:
                del self.typing_users[channel_key]


# Global instance
manager = ConnectionManager()
