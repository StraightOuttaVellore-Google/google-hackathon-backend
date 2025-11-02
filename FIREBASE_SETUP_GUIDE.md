# 🔥 Firebase Setup & Permissions Guide

Complete guide for setting up Firebase Firestore with proper permissions after creating your database.

## 🎯 Quick Answer: Do I Need Security Rules?

**For your current setup: NO, rules are NOT required!**

- ✅ Your backend uses **Admin SDK** → Bypasses all rules (works without them)
- ✅ Your frontend connects via backend API → No direct Firestore access
- ⚠️ Rules are only needed if frontend/mobile apps connect directly to Firestore

**You can proceed without rules, but adding them is recommended for security best practices.**

---

## 📋 Table of Contents

1. [Service Account Setup](#1-service-account-setup)
2. [Firestore Security Rules](#2-firestore-security-rules)
3. [Environment Variables](#3-environment-variables)
4. [IAM Permissions](#4-iam-permissions)
5. [Testing Your Setup](#5-testing-your-setup)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Service Account Setup

### Step 1.1: Generate Service Account Key

1. **Go to Firebase Console**
   - Visit: https://console.firebase.google.com/
   - Select your project

2. **Navigate to Service Accounts**
   - Click the ⚙️ **Settings** icon (top left)
   - Select **Project Settings**
   - Go to **Service Accounts** tab

3. **Generate New Private Key**
   - Click **Generate new private key**
   - Confirm the dialog
   - A JSON file will download automatically

4. **Save the Key File**
   ```bash
   # Recommended location in your project
   mv ~/Downloads/your-project-firebase-adminsdk-xxxxx.json \
      /home/vatsal/Hackathons/GenAIExchange/FullStackR2/currVoiceAgent/backend_working_voiceagent/google-hackathon-backend-5b3907c4ed9eb19dbaa08b898a42a4ee1ea5e5fe/firebase-service-account.json
   ```

5. **Set Proper File Permissions** (Security Best Practice)
   ```bash
   # Make file readable only by owner (600 = rw-------)
   chmod 600 firebase-service-account.json
   
   # Verify permissions
   ls -la firebase-service-account.json
   # Should show: -rw------- (owner read/write only)
   ```

### Step 1.2: Verify Service Account Key Structure

The JSON file should contain these fields:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

---

## 2. Firestore Security Rules

### ⚠️ Do You Actually Need Rules?

**Short Answer: For backend-only setup, NO rules are required!**

Here's why:

#### ✅ **Backend (Admin SDK) - NO Rules Needed**
- Your backend uses **Firebase Admin SDK** (see `firebase_db.py`)
- Admin SDK **bypasses ALL security rules** - it has full access
- Your backend will work perfectly without any rules

#### ⚠️ **Frontend (Client SDK) - Rules Required**
- Only needed if your frontend connects **directly** to Firestore using client SDK
- If your frontend only uses your backend API (REST/WebSocket), **NO rules needed**
- Current frontend connects through backend API → **No rules needed!**

#### 📋 **When You DO Need Rules:**
1. Frontend uses `getFirestore()` from `firebase/firestore` (client SDK)
2. Mobile apps connect directly to Firestore
3. Third-party services access Firestore directly
4. You want an extra layer of protection (defense in depth)

#### 🎯 **Current Setup Status:**
Based on your codebase:
- ✅ Backend uses Admin SDK → **Rules optional**
- ✅ Frontend connects via backend API → **Rules optional**
- ✅ No direct Firestore client SDK usage → **Rules optional**

**Verdict: You can skip rules for now!** But it's good practice to add them anyway for future-proofing.

---

### Step 2.1: Access Firestore Rules (Optional but Recommended)

1. Go to **Firestore Database** in Firebase Console
2. Click **Rules** tab

### Step 2.2: Set Up Security Rules (Optional but Recommended)

Copy and paste these rules based on your collections:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Helper functions
    function isAuthenticated() {
      return request.auth != null;
    }
    
    function isOwner(userId) {
      return isAuthenticated() && request.auth.uid == userId;
    }
    
    // Users Collection
    match /users/{userId} {
      // Users can read/write their own data
      allow read, write: if isOwner(userId);
      
      // Allow creation during signup (no auth required initially)
      allow create: if request.resource.data.keys().hasAll(['email', 'password_hash']);
    }
    
    // Priority Matrix Tasks
    match /priority_matrix_tasks/{taskId} {
      allow read, write: if isAuthenticated() && 
        request.resource.data.user_id == request.auth.uid;
      allow create: if isAuthenticated() && 
        request.resource.data.user_id == request.auth.uid;
      allow delete: if isAuthenticated() && 
        resource.data.user_id == request.auth.uid;
    }
    
    // Reddit Collections
    match /countries/{countryId} {
      allow read: if true; // Public read
      allow write: if false; // Admin only (use service account in backend)
    }
    
    match /reddit_posts/{postId} {
      allow read: if true; // Public read
      allow create: if isAuthenticated();
      allow update, delete: if isAuthenticated() && 
        (resource.data.user_id == request.auth.uid || 
         request.resource.data.user_id == request.auth.uid);
    }
    
    match /reddit_comments/{commentId} {
      allow read: if true; // Public read
      allow create: if isAuthenticated();
      allow update, delete: if isAuthenticated() && 
        (resource.data.user_id == request.auth.uid || 
         request.resource.data.user_id == request.auth.uid);
    }
    
    match /reddit_votes/{voteId} {
      allow read: if isAuthenticated();
      allow create, update, delete: if isAuthenticated() && 
        request.resource.data.user_id == request.auth.uid;
    }
    
    match /country_subscriptions/{subscriptionId} {
      allow read: if isAuthenticated();
      allow create, update, delete: if isAuthenticated() && 
        request.resource.data.user_id == request.auth.uid;
    }
    
    match /reddit_reports/{reportId} {
      allow read: if false; // Admin only
      allow create: if isAuthenticated();
    }
    
    // Wellness Collections
    match /wellness_analyses/{analysisId} {
      allow read, write: if isAuthenticated() && 
        resource.data.user_id == request.auth.uid;
    }
    
    match /wellness_pathways/{pathwayId} {
      allow read, write: if isAuthenticated() && 
        resource.data.user_id == request.auth.uid;
    }
    
    match /agent_recommended_tasks/{taskId} {
      allow read, write: if isAuthenticated() && 
        resource.data.user_id == request.auth.uid;
    }
    
    // Voice Journal Collections
    match /voice_journal_sessions/{sessionId} {
      allow read, write: if isAuthenticated() && 
        resource.data.user_id == request.auth.uid;
    }
    
    match /voice_journal_analyses/{analysisId} {
      allow read, write: if isAuthenticated() && 
        resource.data.user_id == request.auth.uid;
    }
    
    // User-specific nested collections (for MCP server)
    match /users/{userId}/tasks/{taskId} {
      allow read, write: if isOwner(userId);
    }
    
    match /users/{userId}/dailyData/{dataId} {
      allow read, write: if isOwner(userId);
    }
    
    match /users/{userId}/pomodoroSessions/{sessionId} {
      allow read, write: if isOwner(userId);
    }
    
    // Deny all other access
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

### Step 2.3: Publish Rules

1. Click **Publish** button
2. Wait for confirmation

**⚠️ Important:** These rules apply to client-side access. Your backend uses Admin SDK which bypasses these rules. Still configure them for frontend clients!

---

## 3. Environment Variables

### Step 3.1: Create `.env` File

Create a `.env` file in your backend root directory:

```bash
cd /home/vatsal/Hackathons/GenAIExchange/FullStackR2/currVoiceAgent/backend_working_voiceagent/google-hackathon-backend-5b3907c4ed9eb19dbaa08b898a42a4ee1ea5e5fe
```

### Step 3.2: Add Environment Variables

Create/update `.env` with:

```bash
# Firebase Configuration
SERVICE_ACCOUNT_KEY_PATH=/home/vatsal/Hackathons/GenAIExchange/FullStackR2/currVoiceAgent/backend_working_voiceagent/google-hackathon-backend-5b3907c4ed9eb19dbaa08b898a42a4ee1ea5e5fe/firebase-service-account.json
FIREBASE_PROJECT_ID=your-project-id-here

# Alternative (if using GOOGLE_APPLICATION_CREDENTIALS)
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Other environment variables (keep existing ones)
# JWT_SECRET_KEY=...
# CORS_ORIGINS=...
```

### Step 3.3: Secure `.env` File

```bash
# Make .env readable only by owner
chmod 600 .env

# Add .env to .gitignore (if not already)
echo ".env" >> .gitignore
echo "firebase-service-account.json" >> .gitignore
echo "*.json" | grep -v "package.json\|tsconfig.json" >> .gitignore
```

---

## 4. IAM Permissions

### Step 4.1: Verify Service Account Roles

The service account should have these roles in Google Cloud Console:

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Select your Firebase project

2. **Navigate to IAM & Admin > IAM**
   - Find your service account (ends with `@your-project.iam.gserviceaccount.com`)

3. **Required Roles:**
   - ✅ **Firebase Admin SDK Administrator Service Agent** (automatic)
   - ✅ **Cloud Datastore User** (for Firestore)
   - ✅ **Firebase Admin** (full access)

### Step 4.2: Add Missing Roles (if needed)

If roles are missing:

1. Click **Edit** (pencil icon) on the service account
2. Click **ADD ANOTHER ROLE**
3. Add:
   - `Cloud Datastore User`
   - `Firebase Admin`
4. Click **SAVE**

---

## 5. Testing Your Setup

### Step 5.1: Test Firebase Connection

Create a test script:

```bash
cd /home/vatsal/Hackathons/GenAIExchange/FullStackR2/currVoiceAgent/backend_working_voiceagent/google-hackathon-backend-5b3907c4ed9eb19dbaa08b898a42a4ee1ea5e5fe

cat > test_firebase.py << 'EOF'
"""Test Firebase connection and permissions"""
import os
from dotenv import load_dotenv
from firebase_db import initialize_firebase, get_firestore
import logging

logging.basicConfig(level=logging.INFO)
load_dotenv()

def test_firebase():
    try:
        # Initialize Firebase
        print("🔄 Initializing Firebase...")
        initialize_firebase()
        print("✅ Firebase initialized")
        
        # Get Firestore client
        db = get_firestore()
        print("✅ Firestore client obtained")
        
        # Test write operation
        print("\n🔄 Testing write operation...")
        test_ref = db.collection('_test').document('connection_test')
        test_ref.set({
            'status': 'success',
            'timestamp': '2024-11-25T00:00:00Z',
            'message': 'Firebase connection is working!'
        })
        print("✅ Write test successful")
        
        # Test read operation
        print("\n🔄 Testing read operation...")
        doc = test_ref.get()
        if doc.exists:
            print(f"✅ Read test successful: {doc.to_dict()}")
        else:
            print("❌ Document not found")
        
        # Test delete operation
        print("\n🔄 Testing delete operation...")
        test_ref.delete()
        print("✅ Delete test successful")
        
        # Test collection listing
        print("\n🔄 Testing collection access...")
        collections = db.collections()
        collection_names = [col.id for col in collections]
        print(f"✅ Available collections: {collection_names}")
        
        print("\n🎉 All Firebase tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Firebase test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_firebase()
    exit(0 if success else 1)
EOF

# Run the test
python test_firebase.py
```

### Step 5.2: Test Specific Collections

```bash
cat > test_collections.py << 'EOF'
"""Test specific collection access"""
from firebase_db import get_firestore

db = get_firestore()

# Test collections used by your app
collections_to_test = [
    'users',
    'countries',
    'reddit_posts',
    'reddit_comments',
    'priority_matrix_tasks',
    'wellness_analyses',
]

for collection_name in collections_to_test:
    try:
        ref = db.collection(collection_name)
        count = len(list(ref.limit(1).stream()))
        print(f"✅ {collection_name}: Accessible ({count} documents)")
    except Exception as e:
        print(f"❌ {collection_name}: Error - {e}")
EOF

python test_collections.py
```

### Step 5.3: Test Backend Startup

```bash
# Test that your FastAPI app initializes Firebase correctly
python -c "
from main import lifespan
from fastapi import FastAPI
import asyncio

app = FastAPI()

async def test():
    async with lifespan(app):
        print('✅ Backend initialized Firebase successfully')
        return True

asyncio.run(test())
"
```

---

## 6. Troubleshooting

### Issue 1: "Firebase credentials file not found"

**Solution:**
```bash
# Check if file exists
ls -la firebase-service-account.json

# Check environment variable
echo $SERVICE_ACCOUNT_KEY_PATH

# Update .env if needed
nano .env  # or use your preferred editor
```

### Issue 2: "Permission denied" errors

**Solution:**
1. Check file permissions:
   ```bash
   chmod 600 firebase-service-account.json
   ```

2. Verify service account has correct IAM roles (see Section 4)

3. Check if service account email matches in Firebase Console

### Issue 3: "Invalid JSON" error

**Solution:**
```bash
# Validate JSON file
python -m json.tool firebase-service-account.json > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"

# Check for hidden characters
file firebase-service-account.json
```

### Issue 4: "Firestore not enabled"

**Solution:**
1. Go to Firebase Console
2. Navigate to **Firestore Database**
3. Click **Create database** if not exists
4. Choose **Production mode** or **Test mode** (Production for security rules)

### Issue 5: "Project ID mismatch"

**Solution:**
```bash
# Check project ID in service account file
python -c "import json; print(json.load(open('firebase-service-account.json'))['project_id'])"

# Verify FIREBASE_PROJECT_ID matches
grep FIREBASE_PROJECT_ID .env
```

### Issue 6: Collection doesn't exist yet

**Note:** Firestore creates collections automatically on first write. No need to manually create them!

### Issue 7: "Default credentials" error

**Solution:**
- Make sure `SERVICE_ACCOUNT_KEY_PATH` is set in `.env`
- Or set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Don't rely on default credentials unless running on GCP

---

## 7. Security Checklist

Before going to production, verify:

- [ ] Service account key file has `600` permissions (`chmod 600`)
- [ ] `.env` file is in `.gitignore`
- [ ] Service account key JSON is in `.gitignore`
- [ ] Firestore security rules are published
- [ ] Security rules test passed in Firebase Console (Rules > Rules Playground)
- [ ] Service account has minimal required IAM roles
- [ ] Environment variables are loaded correctly
- [ ] Connection test passes
- [ ] All collections are accessible as expected

---

## 8. Quick Start Commands

```bash
# 1. Navigate to backend directory
cd /home/vatsal/Hackathons/GenAIExchange/FullStackR2/currVoiceAgent/backend_working_voiceagent/google-hackathon-backend-5b3907c4ed9eb19dbaa08b898a42a4ee1ea5e5fe

# 2. Set up service account key
# (Download from Firebase Console, then:)
chmod 600 firebase-service-account.json

# 3. Create/update .env
cat > .env << EOF
SERVICE_ACCOUNT_KEY_PATH=$(pwd)/firebase-service-account.json
FIREBASE_PROJECT_ID=your-project-id
EOF
chmod 600 .env

# 4. Test connection
python test_firebase.py

# 5. Start backend
uvicorn main:app --reload
```

---

## 9. Additional Resources

- **Firebase Console**: https://console.firebase.google.com/
- **Firestore Docs**: https://firebase.google.com/docs/firestore
- **Security Rules**: https://firebase.google.com/docs/firestore/security/get-started
- **Service Accounts**: https://cloud.google.com/iam/docs/service-accounts
- **Admin SDK Python**: https://firebase.google.com/docs/admin/setup

---

## ✅ Success Indicators

You've successfully set up Firebase when:

1. ✅ `test_firebase.py` runs without errors
2. ✅ Backend starts and logs: `✅ Firebase initialized successfully`
3. ✅ You can read/write to Firestore collections
4. ✅ No permission errors in logs
5. ✅ Collections appear in Firebase Console

---

**Need help?** Check the troubleshooting section or verify each step above!


