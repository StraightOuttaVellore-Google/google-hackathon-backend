"""
Seed script to populate the database with initial chat servers and channels.
Run this script after setting up the database to create sample servers.

Usage:
    python seed_chat_data.py
"""

import sys
import io

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlmodel import Session, select
from db import engine
from model import (
    ChatServer,
    ChatChannel,
    ServerMembership,
    Users,
    ChannelType,
    ServerRole,
)
import uuid


def seed_chat_data():
    """Create sample servers, channels, and add all users as members"""
    
    with Session(engine) as session:
        print("🌱 Starting chat data seeding...")
        
        # Get all existing users
        users = session.exec(select(Users)).all()
        
        if not users:
            print("❌ No users found in database! Please create at least one user first.")
            return
        
        print(f"✅ Found {len(users)} user(s) in database")
        
        # Use first user as the creator of servers
        creator_id = users[0].user_id
        print(f"📝 Creating servers as user: {users[0].username}")
        
        # Define servers to create
        servers_data = [
            {
                "name": "General Community",
                "icon": "🌍",
                "channels": [
                    {"name": "welcome", "type": ChannelType.TEXT, "position": 0},
                    {"name": "general-chat", "type": ChannelType.TEXT, "position": 1},
                    {"name": "announcements", "type": ChannelType.TEXT, "position": 2},
                    {"name": "Voice Lounge", "type": ChannelType.VOICE, "position": 3},
                ]
            },
            {
                "name": "Study Hub",
                "icon": "📚",
                "channels": [
                    {"name": "study-lounge", "type": ChannelType.TEXT, "position": 0},
                    {"name": "homework-help", "type": ChannelType.TEXT, "position": 1},
                    {"name": "resources", "type": ChannelType.TEXT, "position": 2},
                    {"name": "study-together", "type": ChannelType.VOICE, "position": 3},
                    {"name": "quiet-focus", "type": ChannelType.VOICE, "position": 4},
                ]
            },
            {
                "name": "Wellness & Mindfulness",
                "icon": "🧘",
                "channels": [
                    {"name": "wellness-chat", "type": ChannelType.TEXT, "position": 0},
                    {"name": "meditation-tips", "type": ChannelType.TEXT, "position": 1},
                    {"name": "daily-gratitude", "type": ChannelType.TEXT, "position": 2},
                    {"name": "support-group", "type": ChannelType.TEXT, "position": 3},
                    {"name": "Meditation Room", "type": ChannelType.VOICE, "position": 4},
                ]
            }
        ]
        
        created_servers = []
        
        # Create servers and channels
        for server_data in servers_data:
            # Check if server already exists
            existing_server = session.exec(
                select(ChatServer).where(ChatServer.name == server_data["name"])
            ).first()
            
            if existing_server:
                print(f"⏭️  Server '{server_data['name']}' already exists, skipping...")
                created_servers.append(existing_server)
                continue
            
            # Create server
            server = ChatServer(
                name=server_data["name"],
                icon=server_data["icon"],
                created_by=creator_id,
            )
            session.add(server)
            session.commit()
            session.refresh(server)
            
            print(f"✨ Created server: {server.name} {server.icon}")
            created_servers.append(server)
            
            # Create channels for this server
            for channel_data in server_data["channels"]:
                channel = ChatChannel(
                    server_id=server.id,
                    name=channel_data["name"],
                    type=channel_data["type"],
                    position=channel_data["position"],
                )
                session.add(channel)
                print(f"   📝 Created channel: #{channel.name} ({channel.type.value})")
            
            session.commit()
        
        # Add all users as members to all servers
        print("\n👥 Adding users to servers...")
        for server in created_servers:
            for user in users:
                # Check if membership already exists
                existing_membership = session.exec(
                    select(ServerMembership).where(
                        ServerMembership.server_id == server.id,
                        ServerMembership.user_id == user.user_id,
                    )
                ).first()
                
                if existing_membership:
                    print(f"   ⏭️  {user.username} already member of '{server.name}', skipping...")
                    continue
                
                # Make creator an admin, others regular members
                role = ServerRole.ADMIN if user.user_id == creator_id else ServerRole.MEMBER
                
                membership = ServerMembership(
                    server_id=server.id,
                    user_id=user.user_id,
                    role=role,
                )
                session.add(membership)
                print(f"   ✅ Added {user.username} to '{server.name}' as {role.value}")
        
        session.commit()
        
        print("\n✨ Chat data seeding completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Servers created/verified: {len(created_servers)}")
        print(f"   - Users added to servers: {len(users)}")
        print(f"   - Total memberships: {len(created_servers) * len(users)}")


if __name__ == "__main__":
    try:
        seed_chat_data()
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()

