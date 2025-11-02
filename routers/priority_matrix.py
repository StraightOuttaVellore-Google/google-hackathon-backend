"""
Priority Matrix Router - Firebase Version

Handles Eisenhower Matrix tasks using Firestore for real-time sync.
"""

from typing import Optional, List
import uuid
from fastapi import APIRouter, HTTPException, Response, status
from datetime import date, datetime
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from model import PriorityMatrix, TaskData, DeleteTaskData, TaskStatus, Quadrant
from firebase_db import get_firestore
from utils import TokenDep, get_current_user

router = APIRouter(prefix="/priority_matrix", tags=["PriorityMatrix"])


def _task_dict_to_model(task_id: str, task_dict: dict) -> PriorityMatrix:
    """Convert Firestore document dict to PriorityMatrix model"""
    return PriorityMatrix(
        id=uuid.UUID(task_id),
        user_id=uuid.UUID(task_dict.get('user_id')),
        quadrant=Quadrant(task_dict.get('quadrant')),
        title=task_dict.get('title', ''),
        description=task_dict.get('description', ''),
        status=TaskStatus(task_dict.get('status', TaskStatus.TODO.value)),
        due_date=datetime.fromisoformat(task_dict.get('due_date')).date() if task_dict.get('due_date') else None,
        created_at=datetime.fromisoformat(task_dict.get('created_at')) if task_dict.get('created_at') else datetime.utcnow(),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PriorityMatrix,
)
async def add_task(token_data: TokenDep, data: TaskData):
    """Create a new priority matrix task"""
    try:
        db = get_firestore()
        tasks_ref = db.collection('priority_matrix_tasks')
        
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        task_data = {
            "user_id": token_data.user_id,
            "quadrant": data.quadrant.value,
            "title": data.title,
            "description": data.description,
            "status": data.status.value if data.status else TaskStatus.TODO.value,
            "due_date": data.due_date.isoformat() if data.due_date else None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        tasks_ref.document(task_id).set(task_data)
        
        # Return as PriorityMatrix model
        task_data['id'] = task_id
        return _task_dict_to_model(task_id, task_data)
        
    except Exception as e:
        print(f"Database error in add_task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {e}",
        )


@router.get("", response_model=List[PriorityMatrix])
async def get_priority_matrix(
    token_data: TokenDep,
    day: Optional[str] = None,
    due: Optional[str] = None
):
    """
    Get priority matrix tasks for the user
    
    Args:
        token_data: Authentication token data
        day: Filter by creation date (format: "yyyy-mm-dd")
        due: Filter by due date (format: "yyyy-mm-dd")
    """
    try:
        db = get_firestore()
        tasks_ref = db.collection('priority_matrix_tasks')
        
        # Query by user_id
        query = tasks_ref.where('user_id', '==', token_data.user_id)
        
        # Apply date filters
        if due is not None:
            due_parts = due.split("-")
            due_dt = date(int(due_parts[0]), int(due_parts[1]), int(due_parts[2]))
            due_str = due_dt.isoformat()
            query = query.where('due_date', '==', due_str)
        elif day is not None:
            day_parts = day.split("-")
            day_dt = date(int(day_parts[0]), int(day_parts[1]), int(day_parts[2]))
            day_str = day_dt.isoformat()
            # Filter by created_at date (Firestore stores as ISO string)
            # Note: This is a simple string comparison, may need refinement
            query = query.where('created_at', '>=', f"{day_str}T00:00:00")
            query = query.where('created_at', '<=', f"{day_str}T23:59:59")
        
        # Execute query
        docs = query.stream()
        results = []
        
        for doc in docs:
            task_dict = doc.to_dict()
            results.append(_task_dict_to_model(doc.id, task_dict))
        
        if not results:
            return []
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {e}",
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(token_data: TokenDep, task_data: DeleteTaskData):
    """Delete a priority matrix task"""
    try:
        try:
            task_uuid = uuid.UUID(task_data.id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task ID format",
            )
        
        db = get_firestore()
        task_ref = db.collection('priority_matrix_tasks').document(task_data.id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify ownership
        task_dict = task_doc.to_dict()
        if task_dict.get('user_id') != token_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You can only delete your own tasks"
            )
        
        task_ref.delete()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {e}",
        )


@router.patch("", response_model=PriorityMatrix)
async def update_task(token_data: TokenDep, changed_data: TaskData):
    """Update a priority matrix task"""
    try:
        if not changed_data.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task ID is required for updates"
            )
        
        try:
            task_uuid = uuid.UUID(changed_data.id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task ID format",
            )
        
        db = get_firestore()
        task_ref = db.collection('priority_matrix_tasks').document(changed_data.id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify ownership
        task_dict = task_doc.to_dict()
        if task_dict.get('user_id') != token_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You can only update your own tasks"
            )
        
        # Build update data
        update_data = {
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if changed_data.quadrant:
            update_data["quadrant"] = changed_data.quadrant.value
        if changed_data.title:
            update_data["title"] = changed_data.title
        if changed_data.description:
            update_data["description"] = changed_data.description
        if changed_data.status:
            update_data["status"] = changed_data.status.value
        if changed_data.due_date is not None:
            update_data["due_date"] = changed_data.due_date.isoformat()
        
        # Update document
        task_ref.update(update_data)
        
        # Get updated document
        updated_doc = task_ref.get()
        updated_dict = updated_doc.to_dict()
        
        return _task_dict_to_model(changed_data.id, updated_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {e}",
        )
