"""
Daily Journal Router - Firebase Version

Handles daily journal entries using Firestore for real-time sync.
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime, date
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from typing import Optional

from firebase_db import get_firestore
from model import DailyJournalDataInput
from utils import TokenDep

router = APIRouter(tags=["DailyJournal"])


@router.get("/daily_journal")
async def get_all_daily_journal(token_data: TokenDep):
    """Get all daily journal entries for the current user"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Query all journal entries for this user
        entries_ref = db.collection('daily_journals')
        query = entries_ref.where('user_id', '==', user_id).order_by('journal_date', direction='DESCENDING')
        
        entries = []
        for doc in query.stream():
            data = doc.to_dict()
            entries.append({
                "id": doc.id,
                "journal_date": data.get('journal_date'),
                "study_mode": data.get('study_mode', True),
                "mood": data.get('mood'),
                "stress_level": data.get('stress_level'),
                "notes": data.get('notes'),
                "data": data.get('data'),
                "created_at": data.get('created_at'),
            })
        
        return entries
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving journal entries: {str(e)}"
        )


@router.get("/daily_journal/{date}")
async def get_daily_journal_by_date(date: str, token_data: TokenDep):
    """Get daily journal entry for a specific date (format: YYYY-MM-DD)"""
    try:
        # Parse and validate date
        journal_date = datetime.strptime(date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Query for entry with this date and user_id
        entries_ref = db.collection('daily_journals')
        query = entries_ref.where('user_id', '==', user_id).where('journal_date', '==', journal_date).limit(1)
        
        docs = list(query.stream())
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found for this date"
            )
        
        data = docs[0].to_dict()
        return {
            "id": docs[0].id,
            "journal_date": data.get('journal_date'),
            "study_mode": data.get('study_mode', True),
            "mood": data.get('mood'),
            "stress_level": data.get('stress_level'),
            "notes": data.get('notes'),
            "data": data.get('data'),
            "created_at": data.get('created_at'),
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving journal entry: {str(e)}"
        )


@router.post("/daily_journal", status_code=status.HTTP_201_CREATED)
async def create_daily_journal(data: DailyJournalDataInput, token_data: TokenDep):
    """Create a new daily journal entry"""
    try:
        # Parse and validate date
        journal_date = datetime.strptime(data.journal_date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Check if entry already exists
        entries_ref = db.collection('daily_journals')
        query = entries_ref.where('user_id', '==', user_id).where('journal_date', '==', journal_date).limit(1)
        
        existing_docs = list(query.stream())
        
        journal_data = {
            "user_id": user_id,
            "journal_date": journal_date,
            "study_mode": data.study_mode,
            "mood": data.mood,
            "stress_level": data.stress_level,
            "notes": data.notes,
            "data": data.data,
            "updated_at": SERVER_TIMESTAMP,
        }
        
        if existing_docs:
            # Update existing entry
            existing_docs[0].reference.update(journal_data)
            return {"status": "updated", "id": existing_docs[0].id}
        else:
            # Create new entry
            journal_data["created_at"] = SERVER_TIMESTAMP
            doc_ref = entries_ref.document()
            doc_ref.set(journal_data)
            return {"status": "created", "id": doc_ref.id}
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating journal entry: {str(e)}"
        )


@router.patch("/daily_journal/{date}")
async def update_daily_journal(date: str, data: DailyJournalDataInput, token_data: TokenDep):
    """Update a daily journal entry for a specific date"""
    try:
        # Parse and validate date
        journal_date = datetime.strptime(date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Find existing entry
        entries_ref = db.collection('daily_journals')
        query = entries_ref.where('user_id', '==', user_id).where('journal_date', '==', journal_date).limit(1)
        
        docs = list(query.stream())
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found for this date"
            )
        
        # Update fields
        update_data = {
            "study_mode": data.study_mode,
            "updated_at": SERVER_TIMESTAMP,
        }
        
        if data.mood is not None:
            update_data["mood"] = data.mood
        if data.stress_level is not None:
            update_data["stress_level"] = data.stress_level
        if data.notes is not None:
            update_data["notes"] = data.notes
        if data.data is not None:
            update_data["data"] = data.data
        
        docs[0].reference.update(update_data)
        return {"status": "updated", "id": docs[0].id}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating journal entry: {str(e)}"
        )


@router.delete("/daily_journal/{date}")
async def delete_daily_journal(date: str, token_data: TokenDep):
    """Delete a daily journal entry for a specific date"""
    try:
        # Parse and validate date
        journal_date = datetime.strptime(date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Find existing entry
        entries_ref = db.collection('daily_journals')
        query = entries_ref.where('user_id', '==', user_id).where('journal_date', '==', journal_date).limit(1)
        
        docs = list(query.stream())
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found for this date"
            )
        
        # Delete entry
        docs[0].reference.delete()
        return {"status": "deleted", "id": docs[0].id}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting journal entry: {str(e)}"
        )
