"""
Update all chat servers to include all current users
Ensures every user in Firebase can see all servers
"""

from firebase_db import get_firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP, ArrayUnion
import sys

def update_servers_with_all_users():
    """Update all servers to include all current users in member_ids"""
    
    db = get_firestore()
    print("🔄 Updating servers to include all users...")
    
    # Get ALL users
    users_ref = db.collection('users')
    users_query = users_ref.stream()
    users = list(users_query)
    
    if not users:
        print("⚠️  No users found in Firebase!")
        return
    
    user_ids = [doc.id for doc in users]
    print(f"✅ Found {len(user_ids)} user(s) in Firebase")
    print(f"   User IDs: {user_ids}")
    
    # Get all servers
    servers_ref = db.collection('chatServers')
    servers = list(servers_ref.stream())
    
    if not servers:
        print("⚠️  No servers found! Run seed_chat_firebase.py first.")
        return
    
    print(f"📊 Found {len(servers)} server(s)")
    print()
    
    # Update each server
    for server_doc in servers:
        server_id = server_doc.id
        server_data = server_doc.to_dict()
        server_name = server_data.get('name', 'Unknown')
        
        print(f"🔧 Updating server: {server_name} ({server_id})")
        
        # Get current member_ids
        current_member_ids = set(server_data.get('member_ids', []))
        
        # Add all user IDs
        updated_member_ids = current_member_ids.union(set(user_ids))
        
        # Only update if there are new users to add
        if len(updated_member_ids) > len(current_member_ids):
            server_ref = db.collection('chatServers').document(server_id)
            server_ref.update({
                'member_ids': list(updated_member_ids),
                'updated_at': SERVER_TIMESTAMP
            })
            print(f"   ✅ Updated: Added {len(updated_member_ids) - len(current_member_ids)} new user(s)")
            print(f"   📝 Total members now: {len(updated_member_ids)}")
        else:
            print(f"   ✅ Already up to date ({len(updated_member_ids)} members)")
        
        # Ensure serverMemberships exist for all users
        memberships_ref = db.collection('serverMemberships')
        membership_count = 0
        for user_id in user_ids:
            # Check if membership exists
            existing = memberships_ref.where('server_id', '==', server_id)\
                                    .where('user_id', '==', user_id)\
                                    .limit(1)\
                                    .stream()
            if not list(existing):
                # Create membership
                import uuid
                membership_id = str(uuid.uuid4())
                role = "admin" if user_id == server_data.get('created_by') else "member"
                
                memberships_ref.document(membership_id).set({
                    "server_id": server_id,
                    "user_id": user_id,
                    "role": role,
                    "joined_at": SERVER_TIMESTAMP,
                })
                membership_count += 1
        
        if membership_count > 0:
            print(f"   👥 Created {membership_count} new membership(s)")
        print()
    
    print("✨ Update completed successfully!")
    print(f"📊 All {len(servers)} server(s) now include all {len(user_ids)} user(s)")


if __name__ == "__main__":
    try:
        update_servers_with_all_users()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


