"""
Firebase Chat Data Seeder
Seeds Firestore with Discord-style chat servers, channels, and memberships.

Usage:
    python seed_chat_firebase.py
"""

import sys
from firebase_db import get_firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import uuid
from datetime import datetime

def seed_chat_firebase():
    """Create sample chat servers and channels in Firebase"""
    
    db = get_firestore()
    print("🌱 Starting Firebase chat data seeding...")
    
    # Get existing users to add as members (get all users, not just 10)
    users_ref = db.collection('users')
    users_query = users_ref.stream()  # Removed .limit(10) to get ALL users
    users = list(users_query)
    
    if not users:
        print("⚠️  No users found in Firebase. Creating servers anyway...")
        print("   Users can join servers later through the UI.")
        user_ids = []
    else:
        user_ids = [doc.id for doc in users]
        print(f"✅ Found {len(users)} user(s) in Firebase")
        print(f"   Users: {', '.join([doc.to_dict().get('username', doc.id) for doc in users[:3]])}...")
    
    # Use first user as creator, or 'system' if no users
    creator_id = user_ids[0] if user_ids else 'system'
    
    # Define servers to create
    servers_data = [
        {
            "name": "General Community",
            "icon": "🌍",
            "description": "Welcome to the community! Share ideas, ask questions, and connect.",
            "channels": [
                {"name": "welcome", "type": "text", "position": 0, "description": "New? Start here!"},
                {"name": "general-chat", "type": "text", "position": 1, "description": "General discussions"},
                {"name": "announcements", "type": "text", "position": 2, "description": "Important updates"},
                {"name": "Voice Lounge", "type": "voice", "position": 3, "description": "Casual voice chat"},
            ]
        },
        {
            "name": "Study Hub",
            "icon": "📚",
            "description": "Collaborate on studies, share resources, and stay motivated together.",
            "channels": [
                {"name": "study-lounge", "type": "text", "position": 0, "description": "Main study chat"},
                {"name": "homework-help", "type": "text", "position": 1, "description": "Get help with assignments"},
                {"name": "resources", "type": "text", "position": 2, "description": "Share study materials"},
                {"name": "exam-prep", "type": "text", "position": 3, "description": "Exam preparation tips"},
                {"name": "study-together", "type": "voice", "position": 4, "description": "Study with others"},
                {"name": "quiet-focus", "type": "voice", "position": 5, "description": "Silent study room"},
            ]
        },
        {
            "name": "Wellness & Mindfulness",
            "icon": "🧘",
            "description": "A safe space for mental health, meditation, and self-care discussions.",
            "channels": [
                {"name": "wellness-chat", "type": "text", "position": 0, "description": "General wellness talk"},
                {"name": "meditation-tips", "type": "text", "position": 1, "description": "Meditation & mindfulness"},
                {"name": "daily-gratitude", "type": "text", "position": 2, "description": "Share daily gratitude"},
                {"name": "support-group", "type": "text", "position": 3, "description": "Support and encouragement"},
                {"name": "mental-health", "type": "text", "position": 4, "description": "Mental health resources"},
                {"name": "Meditation Room", "type": "voice", "position": 5, "description": "Guided meditation"},
            ]
        }
    ]
    
    created_servers = []
    
    # Create servers and channels
    for server_data in servers_data:
        # Check if server already exists
        existing_query = db.collection('chatServers').where('name', '==', server_data['name']).limit(1)
        existing = list(existing_query.stream())
        
        if existing:
            print(f"⏭️  Server '{server_data['name']}' already exists, skipping...")
            created_servers.append(existing[0])
            continue
        
        # Create server document
        server_id = str(uuid.uuid4())
        server_ref = db.collection('chatServers').document(server_id)
        
        server_doc = {
            "name": server_data["name"],
            "icon": server_data["icon"],
            "description": server_data.get("description", ""),
            "created_by": creator_id,
            "member_ids": user_ids,  # Add all users as members
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
        }
        
        server_ref.set(server_doc)
        print(f"✨ Created server: {server_data['name']} {server_data['icon']}")
        created_servers.append(server_ref)
        
        # Create channels subcollection
        channels_ref = server_ref.collection('channels')
        for channel_data in server_data["channels"]:
            channel_id = str(uuid.uuid4())
            channel_doc = {
                "name": channel_data["name"],
                "type": channel_data["type"],
                "position": channel_data["position"],
                "description": channel_data.get("description", ""),
                "created_at": SERVER_TIMESTAMP,
            }
            channels_ref.document(channel_id).set(channel_doc)
            
            channel_type = "🎤" if channel_data["type"] == "voice" else "#"
            print(f"   📝 Created channel: {channel_type}{channel_data['name']}")
        
        # Create server memberships for each user
        if user_ids:
            memberships_ref = db.collection('serverMemberships')
            membership_count = 0
            for user_id in user_ids:
                # Check if membership already exists
                existing_membership = memberships_ref.where('server_id', '==', server_id)\
                                                     .where('user_id', '==', user_id)\
                                                     .limit(1)\
                                                     .stream()
                if list(existing_membership):
                    continue  # Skip if already exists
                
                membership_id = str(uuid.uuid4())
                role = "admin" if user_id == creator_id else "member"
                
                membership_doc = {
                    "server_id": server_id,
                    "user_id": user_id,
                    "role": role,
                    "joined_at": SERVER_TIMESTAMP,
                }
                memberships_ref.document(membership_id).set(membership_doc)
                membership_count += 1
            
            if membership_count > 0:
                print(f"   👥 Added {membership_count} new members to server")
            else:
                print(f"   👥 All {len(user_ids)} members already in server")
    
    print("\n✨ Firebase chat data seeding completed successfully!")
    print(f"📊 Summary:")
    print(f"   - Servers created: {len([s for s in created_servers if hasattr(s, 'id')])}")
    print(f"   - Users with access: {len(user_ids)}")
    if user_ids:
        print(f"   - Total memberships: {len(created_servers) * len(user_ids)}")
    print(f"\n🎉 Ready to use! Access chat at: http://localhost:3000")
    print(f"   Users can now see and join these servers.")


if __name__ == "__main__":
    try:
        seed_chat_firebase()
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()

