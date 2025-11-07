#!/usr/bin/env python3
"""
Combined script to populate Reddit countries and Discord chat servers
Run this script to seed both Reddit communities and Discord chat data

Usage:
    python populate_reddit_discord.py
"""

import sys
from firebase_db import get_firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import uuid
from datetime import datetime, timedelta

# Reddit countries data
COUNTRIES_DATA = [
    {"iso_code": "US", "name": "United States", "flag_emoji": "🇺🇸", "description": "Connect with wellness enthusiasts from the United States"},
    {"iso_code": "IN", "name": "India", "flag_emoji": "🇮🇳", "description": "Join the wellness community in India"},
    {"iso_code": "GB", "name": "United Kingdom", "flag_emoji": "🇬🇧", "description": "Wellness discussions from the UK"},
    {"iso_code": "CA", "name": "Canada", "flag_emoji": "🇨🇦", "description": "Canadian wellness community"},
    {"iso_code": "AU", "name": "Australia", "flag_emoji": "🇦🇺", "description": "Australia's wellness network"},
    {"iso_code": "DE", "name": "Germany", "flag_emoji": "🇩🇪", "description": "German wellness community"},
    {"iso_code": "FR", "name": "France", "flag_emoji": "🇫🇷", "description": "French wellness discussions"},
    {"iso_code": "JP", "name": "Japan", "flag_emoji": "🇯🇵", "description": "Japanese wellness community"},
    {"iso_code": "BR", "name": "Brazil", "flag_emoji": "🇧🇷", "description": "Brazilian wellness network"},
    {"iso_code": "CN", "name": "China", "flag_emoji": "🇨🇳", "description": "China's wellness community"},
    {"iso_code": "MX", "name": "Mexico", "flag_emoji": "🇲🇽", "description": "Mexican wellness discussions"},
    {"iso_code": "IT", "name": "Italy", "flag_emoji": "🇮🇹", "description": "Italian wellness community"},
]

# Discord servers data
SERVERS_DATA = [
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


def seed_reddit_countries():
    """Seed Reddit countries with posts into Firebase"""
    print("\n🌍 Seeding Reddit countries...")
    db = get_firestore()
    countries_ref = db.collection('countries')
    
    # Get users for posts
    users_ref = db.collection('users')
    users = list(users_ref.stream())
    user_ids = [doc.id for doc in users] if users else []
    user_data = {}
    for user in users:
        user_data[user.id] = user.to_dict().get('username', user.id)
    
    if not user_ids:
        print("  ⚠️  No users found. Creating countries anyway...")
    
    created_count = 0
    updated_count = 0
    total_posts = 0
    
    for country_data in COUNTRIES_DATA:
        query = countries_ref.where('iso_code', '==', country_data["iso_code"]).limit(1)
        existing_docs = list(query.stream())
        
        now = datetime.utcnow().isoformat()
        
        if existing_docs:
            country_doc = existing_docs[0]
            country_id = country_doc.id
            country_ref = countries_ref.document(country_id)
            country_ref.update({
                "name": country_data["name"],
                "flag_emoji": country_data["flag_emoji"],
                "description": country_data["description"],
                "is_active": True,
                "updated_at": now,
            })
            updated_count += 1
            print(f"  ✅ Updated: {country_data['flag_emoji']} {country_data['name']}")
        else:
            country_doc = countries_ref.add({
                **country_data,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            })[1]
            country_id = country_doc.id
            created_count += 1
            print(f"  ✨ Created: {country_data['flag_emoji']} {country_data['name']}")
        
        # Add sample posts for each country
        if user_ids:
            posts_ref = db.collection('reddit_posts')
            existing_posts = list(posts_ref.where('country_id', '==', country_id).limit(1).stream())
            
            if existing_posts:
                print(f"     ⏭️  Country already has posts")
                continue
            
            post_count = 0
            for i, post_data in enumerate(REDDIT_POSTS[:3]):  # Add 3 posts per country
                user_id = user_ids[i % len(user_ids)]
                username = user_data.get(user_id, f"User{user_id[:4]}")
                
                # Create post with timestamp (older posts first)
                post_time = datetime.utcnow() - timedelta(hours=(3 - i))
                
                post_doc = {
                    "country_id": country_id,
                    "user_id": user_id,
                    "title": post_data["title"],
                    "content": post_data["content"],
                    "media_urls": {},
                    "score": 5 + i * 2,  # Varying scores
                    "comment_count": 0,
                    "is_pinned": i == 0,  # First post is pinned
                    "is_hidden": False,
                    "created_at": post_time.isoformat(),
                    "updated_at": post_time.isoformat(),
                }
                posts_ref.add(post_doc)
                post_count += 1
                total_posts += 1
            
            if post_count > 0:
                print(f"     📝 Added {post_count} posts")
    
    print(f"\n  📊 Reddit: {created_count} created, {updated_count} updated, {total_posts} posts")
    return (created_count + updated_count, total_posts)


# Sample Discord messages for each channel
DISCORD_MESSAGES = {
    "welcome": [
        "Hey everyone! 👋 Welcome to the community!",
        "Thanks for the warm welcome! Excited to be here!",
        "Great to see new faces! Feel free to ask any questions.",
        "This community has been so helpful for my wellness journey!",
    ],
    "general-chat": [
        "How's everyone doing today?",
        "Just finished a great meditation session! 🧘",
        "Anyone up for a study session later?",
        "Sharing some wellness tips: Remember to stay hydrated! 💧",
        "Love the positive energy in this community!",
    ],
    "announcements": [
        "📢 New wellness challenge starting next week!",
        "Reminder: Community meetup this Saturday at 3 PM",
        "We've reached 1000 members! 🎉",
    ],
    "study-lounge": [
        "Starting a 25-minute study session now. Anyone joining?",
        "Just finished my pomodoro! Taking a 5-min break",
        "Pro tip: Use the Pomodoro technique for better focus!",
        "Need help with calculus? Anyone available?",
    ],
    "homework-help": [
        "Stuck on this physics problem. Can someone help?",
        "I can help with that! What's the question?",
        "Study groups are forming for the midterm next week",
    ],
    "wellness-chat": [
        "Started daily gratitude journaling and it's been amazing!",
        "Mindfulness meditation has really helped with my stress",
        "Anyone else trying the 5-minute breathing exercise?",
    ],
    "meditation-tips": [
        "Try guided meditation apps if you're new to meditation",
        "Morning meditation sets the tone for the whole day",
        "Consistency > duration. Even 5 minutes daily helps!",
    ],
    "daily-gratitude": [
        "Today I'm grateful for this supportive community 🌟",
        "Grateful for my health and family today",
        "Thankful for the opportunity to learn and grow",
    ],
}

# Sample Reddit posts for each country
REDDIT_POSTS = [
    {
        "title": "Welcome to our wellness community! 🌟",
        "content": "This is a safe space to share experiences, ask questions, and support each other on our wellness journeys. Feel free to introduce yourself!",
    },
    {
        "title": "Daily Gratitude Thread",
        "content": "What are you grateful for today? Share something positive that happened in your life!",
    },
    {
        "title": "Wellness Tips & Resources",
        "content": "Let's share helpful resources, tips, and strategies for maintaining mental and physical wellness. What has worked for you?",
    },
    {
        "title": "Study Motivation Monday",
        "content": "Starting the week strong! Share your study goals and let's motivate each other to achieve them. 💪",
    },
    {
        "title": "Meditation & Mindfulness Discussion",
        "content": "How has meditation or mindfulness practice impacted your daily life? Share your experiences and favorite techniques!",
    },
]


def seed_discord_servers():
    """Seed Discord chat servers with messages into Firebase"""
    print("\n💬 Seeding Discord chat servers...")
    db = get_firestore()
    
    # Get existing users
    users_ref = db.collection('users')
    users = list(users_ref.stream())
    user_ids = [doc.id for doc in users] if users else []
    user_data = {}
    for user in users:
        user_data[user.id] = user.to_dict().get('username', user.id)
    
    if not user_ids:
        print("  ⚠️  No users found. Creating servers anyway...")
        creator_id = 'system'
        user_data['system'] = 'System'
    else:
        creator_id = user_ids[0]
        print(f"  ✅ Found {len(user_ids)} user(s)")
    
    created_servers = 0
    total_messages = 0
    
    for server_data in SERVERS_DATA:
        # Check if server exists or get existing
        existing_query = db.collection('chatServers').where('name', '==', server_data['name']).limit(1)
        existing = list(existing_query.stream())
        
        if existing:
            server_ref = existing[0].reference
            server_id = existing[0].id
            print(f"  ⏭️  Server '{server_data['name']}' already exists, adding messages...")
        else:
            # Create server
            server_id = str(uuid.uuid4())
            server_ref = db.collection('chatServers').document(server_id)
            
            server_doc = {
                "name": server_data["name"],
                "icon": server_data["icon"],
                "description": server_data.get("description", ""),
                "created_by": creator_id,
                "member_ids": user_ids,
                "created_at": SERVER_TIMESTAMP,
                "updated_at": SERVER_TIMESTAMP,
            }
            
            server_ref.set(server_doc)
            print(f"  ✨ Created server: {server_data['icon']} {server_data['name']}")
            created_servers += 1
        
        # Create channels and messages
        channels_ref = server_ref.collection('channels')
        messages_ref = server_ref.collection('messages')
        channels_created = []
        
        for channel_data in server_data["channels"]:
            # Check if channel exists
            existing_channels = list(channels_ref.where('name', '==', channel_data['name']).stream())
            if existing_channels:
                channel_id = existing_channels[0].id
                print(f"     ⏭️  Channel #{channel_data['name']} exists")
            else:
                channel_id = str(uuid.uuid4())
                channel_doc = {
                    "name": channel_data["name"],
                    "type": channel_data["type"],
                    "position": channel_data["position"],
                    "description": channel_data.get("description", ""),
                    "created_at": SERVER_TIMESTAMP,
                }
                channels_ref.document(channel_id).set(channel_doc)
            
            channels_created.append((channel_id, channel_data['name']))
            
            # Add messages to text channels
            if channel_data["type"] == "text":
                channel_name = channel_data["name"]
                messages = DISCORD_MESSAGES.get(channel_name, [])
                
                # Check existing messages for this channel
                existing_messages = [m for m in list(messages_ref.stream()) 
                                   if m.to_dict().get('channel_id') == channel_id]
                if existing_messages:
                    print(f"     ⏭️  Channel #{channel_name} already has {len(existing_messages)} messages")
                    continue
                
                # Add messages
                message_count = 0
                for i, message_text in enumerate(messages):
                    if not user_ids:
                        break
                    user_id = user_ids[i % len(user_ids)]
                    username = user_data.get(user_id, f"User{user_id[:4]}")
                    
                    # Create timestamps with delays (older messages first)
                    now = datetime.utcnow()
                    message_time = now - timedelta(minutes=(len(messages) - i))
                    
                    message_doc = {
                        "channel_id": channel_id,
                        "user_id": user_id,
                        "username": username,
                        "text": message_text,
                        "created_at": message_time.isoformat(),
                    }
                    messages_ref.add(message_doc)
                    message_count += 1
                    total_messages += 1
                
                if message_count > 0:
                    print(f"     💬 Added {message_count} messages to #{channel_name}")
        
        if not existing:
            print(f"     📝 Created {len(channels_created)} channels")
        
        # Create memberships
        if user_ids:
            memberships_ref = db.collection('serverMemberships')
            membership_count = 0
            for user_id in user_ids:
                existing_membership = memberships_ref.where('server_id', '==', server_id)\
                                                     .where('user_id', '==', user_id)\
                                                     .limit(1)\
                                                     .stream()
                if list(existing_membership):
                    continue
                
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
    
    print(f"\n  📊 Discord: {created_servers} servers, {total_messages} messages")
    return (created_servers, total_messages)


def main():
    """Main function to populate both Reddit and Discord"""
    print("=" * 60)
    print("🌱 Populating Reddit & Discord Data")
    print("=" * 60)
    
    try:
        # Seed Reddit countries
        reddit_count, reddit_posts = seed_reddit_countries()
        
        # Seed Discord servers
        discord_servers, discord_messages = seed_discord_servers()
        
        # Summary
        print("\n" + "=" * 60)
        print("🎉 Population Complete!")
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   🌍 Reddit: {reddit_count} countries, {reddit_posts} posts")
        print(f"   💬 Discord: {discord_servers} servers, {discord_messages} messages")
        print(f"\n✅ Ready to use! Users can now:")
        print(f"   - Browse Reddit communities with sample posts")
        print(f"   - Join Discord chat servers with sample messages")
        
    except Exception as e:
        print(f"\n❌ Error during population: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

