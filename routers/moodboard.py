"""
Moodboard Router - Firebase Version

Handles moodboard data using Firestore for real-time sync.
"""

from fastapi import APIRouter, HTTPException, status
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from firebase_db import get_firestore
from model import MoodboardDataInput
from utils import TokenDep

router = APIRouter(tags=["Moodboard"])


@router.get("/moodboard")
async def get_moodboard_data(token_data: TokenDep):
    """Get moodboard data for the current user"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Query for user's moodboard
        moodboards_ref = db.collection('moodboards')
        query = moodboards_ref.where('user_id', '==', user_id).limit(1)
        
        docs = list(query.stream())
        
        if not docs:
            # Return default data if none exists
            return {"study_mode": True, "data": {}}
        
        data = docs[0].to_dict()
        return {
            "id": docs[0].id,
            "study_mode": data.get('study_mode', True),
            "data": data.get('data') or {},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving moodboard data: {str(e)}"
        )


@router.post("/moodboard", status_code=status.HTTP_201_CREATED)
async def create_moodboard_data(data: MoodboardDataInput, token_data: TokenDep):
    """Create or update moodboard data for the current user"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Check if moodboard already exists
        moodboards_ref = db.collection('moodboards')
        query = moodboards_ref.where('user_id', '==', user_id).limit(1)
        
        existing_docs = list(query.stream())
        
        moodboard_data = {
            "user_id": user_id,
            "study_mode": data.study_mode,
            "data": data.data or {},
            "updated_at": SERVER_TIMESTAMP,
        }
        
        if existing_docs:
            # Update existing data
            existing_docs[0].reference.update(moodboard_data)
            return {"status": "updated", "id": existing_docs[0].id}
        else:
            # Create new moodboard
            moodboard_data["created_at"] = SERVER_TIMESTAMP
            doc_ref = moodboards_ref.document()
            doc_ref.set(moodboard_data)
            return {"status": "created", "id": doc_ref.id}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating/updating moodboard: {str(e)}"
        )


@router.patch("/moodboard")
async def update_moodboard_data(data: MoodboardDataInput, token_data: TokenDep):
    """Update moodboard data for the current user"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Find existing moodboard
        moodboards_ref = db.collection('moodboards')
        query = moodboards_ref.where('user_id', '==', user_id).limit(1)
        
        docs = list(query.stream())
        
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Moodboard data not found. Please create data first."
            )
        
        # Update fields
        update_data = {
            "study_mode": data.study_mode,
            "updated_at": SERVER_TIMESTAMP,
        }
        
        if data.data is not None:
            update_data["data"] = data.data
        
        docs[0].reference.update(update_data)
        return {"status": "updated", "id": docs[0].id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating moodboard: {str(e)}"
        )
