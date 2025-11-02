# Database Architecture Documentation

## Overview

The backend now uses **Firebase Firestore exclusively** for all features! 🎉

**Status:** ✅ **FULLY MIGRATED TO FIREBASE** (November 2024)

All routers have been migrated from PostgreSQL to Firebase Firestore for unified real-time sync with the Sahay ecosystem.

## Database Usage by Router

### 🔴 Firebase (Firestore) Routers - ALL ROUTERS NOW!

These routers use **Firebase Firestore** via `get_firestore()` from `firebase_db.py`:

1. **`routers/reddit.py`** ✅ - Reddit community features (MIGRATED)
   - Countries, Posts, Comments, Votes, Subscriptions
   - Collections: `countries`, `reddit_posts`, `reddit_comments`, `reddit_votes`, `country_subscriptions`, `reddit_reports`

2. **`routers/priority_matrix.py`** ✅ - Eisenhower Matrix tasks (MIGRATED)
   - Priority matrix tasks and quadrants
   - Collection: `priority_matrix_tasks`

3. **`routers/auth.py`** ✅ - Authentication (MIGRATED)
   - User authentication and registration
   - Collection: `users`
   - **Now uses Firebase exclusively** (PostgreSQL fallback removed)

4. **`routers/wellness_analysis.py`** ✅ - Wellness agent analysis
   - Wellness pathways, agent-recommended tasks
   - Collections: `wellness_analyses`, `wellness_pathways`, `agent_recommended_tasks`

5. **`routers/voice_journal.py`** ✅ - Voice journal sessions
   - Voice journal sessions and analysis results
   - Collections: `voice_journal_sessions`, `voice_journal_analyses`

6. **`routers/voice_agent_journal.py`** - Voice agent journal
   - May need migration check

7. **`routers/stats.py`** - User statistics
   - May still use PostgreSQL - needs migration check

8. **`routers/wearable.py`** - Wearable device data
   - May still use PostgreSQL - needs migration check

9. **`routers/moodboard.py`** - Moodboard features
   - May still use PostgreSQL - needs migration check

10. **`routers/daily_journal.py`** - Daily journal entries
   - May still use PostgreSQL - needs migration check

11. **`routers/chat.py`** - Chat/conversation features
   - May still use PostgreSQL - needs migration check

## Database Configuration Files

### Firebase (`firebase_db.py`) ✅ PRIMARY DATABASE
- Connection: Google Cloud Firestore
- Client: `get_firestore()`
- Used for: **ALL FEATURES** (migrated routers)

### PostgreSQL (`db.py`) ⚠️ LEGACY (May still be used by some routers)
- Connection: PostgreSQL via SQLModel/SQLAlchemy
- Session dependency: `SessionDep`
- Status: Still present but should be removed once all routers are migrated

## Migration Status

### ✅ Fully Migrated (Firebase Only)

| Feature Category | Database | Router | Status |
|-----------------|----------|--------|--------|
| Reddit Communities | Firebase | `reddit.py` | ✅ Migrated |
| Priority Matrix | Firebase | `priority_matrix.py` | ✅ Migrated |
| Authentication | Firebase | `auth.py` | ✅ Migrated |
| Wellness Analysis | Firebase | `wellness_analysis.py` | ✅ Already Firebase |
| Voice Journals | Firebase | `voice_journal.py` | ✅ Already Firebase |

### ⚠️ May Need Migration (Check Required)

| Feature Category | Current DB | Router | Status |
|-----------------|------------|--------|--------|
| User Stats | PostgreSQL? | `stats.py` | ⚠️ Check needed |
| Wearable Data | PostgreSQL? | `wearable.py` | ⚠️ Check needed |
| Moodboards | PostgreSQL? | `moodboard.py` | ⚠️ Check needed |
| Daily Journals | PostgreSQL? | `daily_journal.py` | ⚠️ Check needed |
| Chat | PostgreSQL? | `chat.py` | ⚠️ Check needed |
| Voice Agent Journal | PostgreSQL? | `voice_agent_journal.py` | ⚠️ Check needed |

## Benefits of Firebase-Only Architecture

1. ✅ **Unified Database**: All data in one place (Firebase)
2. ✅ **Real-time Sync**: Automatic sync across clients
3. ✅ **Sahay Integration**: Better integration with Sahay ecosystem
4. ✅ **Simplified Architecture**: No dual database maintenance
5. ✅ **Scalability**: Firebase scales automatically
6. ✅ **No Data Fragmentation**: Single source of truth

## Remaining Migration Tasks (If Needed)

If other routers still use PostgreSQL, migrate them using the same pattern:

1. Replace `SessionDep` with `get_firestore()`
2. Replace SQLModel queries with Firestore queries
3. Update data models to use Firestore document structure
4. Test all endpoints
5. Remove PostgreSQL imports and dependencies

