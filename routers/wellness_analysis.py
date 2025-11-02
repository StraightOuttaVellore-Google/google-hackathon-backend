"""
Wellness Analysis Router - Firebase Version

Endpoints for triggering and managing wellness agent analysis,
wellness pathways, and agent-recommended tasks using Firestore.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import date, timedelta, datetime
import uuid
import sys
import logging
from pathlib import Path
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

logger = logging.getLogger(__name__)

# Add agents directory to path
agents_path = Path(__file__).parent.parent / "agents"
sys.path.insert(0, str(agents_path))

from model import (
    TriggerAnalysisInput,
    VoiceJournalAnalysisResult,
    RegisterPathwayInput,
    AddAgentTaskInput,
    Quadrant,
    TaskStatus,
)
from firebase_db import get_firestore
from utils import get_current_user

# Import orchestrator
try:
    from agents.orchestrator import sync_run_wellness_analysis, map_priority_to_quadrant, calculate_due_date
except ImportError as e:
    print(f"Warning: Could not import orchestrator: {e}")
    sync_run_wellness_analysis = None

router = APIRouter(prefix="/wellness", tags=["wellness_analysis"])


@router.post("/analyze", response_model=VoiceJournalAnalysisResult)
async def trigger_wellness_analysis(
    input_data: TriggerAnalysisInput,
    current_user = Depends(get_current_user),
):
    """
    Trigger wellness agent analysis on voice journal transcript
    
    This endpoint:
    1. Runs the appropriate agent (study or general) based on mode
    2. Returns structured analysis with transcript summary and recommendations
    3. Summary goes under transcript, recommendations/tasks go in stats area
    """
    if sync_run_wellness_analysis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness analysis service is not available"
        )
    
    try:
        # Run analysis
        result = sync_run_wellness_analysis(
            transcript=input_data.transcript,
            mode=input_data.mode.value,
            user_id=str(current_user.user_id),
            session_id=None
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/pathways/register")
async def register_wellness_pathway(
    pathway_input: RegisterPathwayInput,
    current_user = Depends(get_current_user),
):
    """
    Register user for a wellness pathway suggested by agents
    
    When user clicks on a suggested pathway, this endpoint:
    1. Creates a WellnessPathway record with REGISTERED status in Firestore
    2. Sets start date and calculates expected completion date
    3. Returns the registered pathway
    """
    try:
        db = get_firestore()
        user_id = str(current_user.user_id)
        
        # Find existing suggested pathway or create new
        pathways_ref = db.collection('wellnessPathways')
        query = pathways_ref.where('user_id', '==', user_id)\
                           .where('pathway_name', '==', pathway_input.pathway_name)\
                           .where('status', '==', 'SUGGESTED')\
                           .limit(1)
        
        existing_pathways = list(query.stream())
        
        started_date = date.today()
        expected_completion = started_date + timedelta(days=pathway_input.duration_days)
        
        if existing_pathways:
            # Update existing pathway
            pathway_doc = existing_pathways[0]
            pathway_ref = pathways_ref.document(pathway_doc.id)
            pathway_ref.update({
                "status": "REGISTERED",
                "started_date": started_date.isoformat(),
                "progress_percentage": 0,
                "updated_at": SERVER_TIMESTAMP,
            })
            pathway_id = pathway_doc.id
        else:
            # Create new pathway
            pathway_data = {
                "user_id": user_id,
                "pathway_name": pathway_input.pathway_name,
                "pathway_type": pathway_input.pathway_type,
                "description": pathway_input.description,
                "duration_days": pathway_input.duration_days,
                "status": "REGISTERED",
                "started_date": started_date.isoformat(),
                "progress_percentage": 0,
                "created_at": SERVER_TIMESTAMP,
                "updated_at": SERVER_TIMESTAMP,
            }
            
            pathway_ref = pathways_ref.document()
            pathway_ref.set(pathway_data)
            pathway_id = pathway_ref.id
        
        return {
            "message": "Pathway registered successfully",
            "pathway_id": pathway_id,
            "pathway_name": pathway_input.pathway_name,
            "started_date": started_date.isoformat(),
            "expected_completion": expected_completion.isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register pathway: {str(e)}"
        )


@router.get("/pathways")
async def get_user_pathways(
    current_user = Depends(get_current_user),
):
    """Get all wellness pathways for current user from Firestore"""
    try:
        db = get_firestore()
        user_id = str(current_user.user_id)
        
        # Query only by user_id to avoid composite index requirement
        pathways_ref = db.collection('wellnessPathways')
        query = pathways_ref.where('user_id', '==', user_id)
        
        pathways_docs = list(query.stream())
        
        # Build pathways list
        pathways = []
        for doc in pathways_docs:
            data = doc.to_dict()
            data['pathway_id'] = doc.id  # Add document ID
            pathways.append(data)
        
        # Sort by created_at in Python (descending - newest first)
        pathways.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        return {"pathways": pathways}
    except Exception as e:
        logger.error(f"Error retrieving pathways: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving pathways: {str(e)}"
        )


@router.patch("/pathways/{pathway_id}/progress")
async def update_pathway_progress(
    pathway_id: str,
    progress: int,
    current_user = Depends(get_current_user),
):
    """Update progress on a wellness pathway in Firestore"""
    try:
        db = get_firestore()
        user_id = str(current_user.user_id)
        
        pathway_ref = db.collection('wellnessPathways').document(pathway_id)
        pathway_doc = pathway_ref.get()
        
        if not pathway_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pathway not found"
            )
        
        pathway_data = pathway_doc.to_dict()
        if pathway_data.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this pathway"
            )
        
        progress = min(100, max(0, progress))
        update_data = {
            "progress_percentage": progress,
            "updated_at": SERVER_TIMESTAMP,
        }
        
        if progress == 100:
            update_data["status"] = "COMPLETED"
            update_data["completed_date"] = date.today().isoformat()
        elif progress > 0:
            update_data["status"] = "IN_PROGRESS"
        
        pathway_ref.update(update_data)
        
        # Get updated document
        updated_doc = pathway_ref.get()
        updated_data = updated_doc.to_dict()
        updated_data['pathway_id'] = pathway_id
        
        return {"message": "Progress updated", "pathway": updated_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update progress: {str(e)}"
        )


@router.post("/tasks/add-from-recommendation")
async def add_task_from_recommendation(
    task_input: AddAgentTaskInput,
    current_user = Depends(get_current_user),
):
    """
    Add a task from agent recommendations to Eisenhower Matrix (Firestore)
    
    This endpoint:
    1. Takes agent-recommended task
    2. Calculates due date based on suggested_due_days
    3. Adds to Firestore priority_matrix_tasks collection
    4. Task shows up in Priority Matrix with real-time sync
    """
    try:
        db = get_firestore()
        user_id = str(current_user.user_id)
        
        # Calculate due date
        due_date_obj = date.today() + timedelta(days=task_input.due_days_from_now)
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Add to priority_matrix_tasks collection (same as priority_matrix router uses)
        tasks_ref = db.collection('priority_matrix_tasks')
        
        task_data = {
            "user_id": user_id,
            "title": task_input.task_title,
            "description": task_input.task_description,
            "quadrant": task_input.quadrant.value if isinstance(task_input.quadrant, Quadrant) else task_input.quadrant,
            "status": TaskStatus.TODO.value,
            "due_date": due_date_obj.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        # Create task document with explicit ID
        tasks_ref.document(task_id).set(task_data)
        
        logger.info(f"✅ Task added to priority matrix: {task_input.task_title}")
        
        return {
            "message": "Task added successfully to Eisenhower Matrix",
            "task_id": task_id,
            "due_date": due_date_obj.isoformat(),
            "quadrant": task_data["quadrant"],
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to add task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add task: {str(e)}"
        )


@router.get("/tasks/recommended")
async def get_recommended_tasks(
    current_user = Depends(get_current_user),
):
    """Get all agent-recommended tasks for current user from Firestore"""
    try:
        db = get_firestore()
        user_id = str(current_user.user_id)
        
        tasks_ref = db.collection('agentRecommendedTasks')
        query = tasks_ref.where('user_id', '==', user_id)\
                        .order_by('due_date')
        
        tasks_docs = query.stream()
        
        tasks = []
        for doc in tasks_docs:
            data = doc.to_dict()
            data['task_id'] = doc.id  # Add document ID
            tasks.append(data)
        
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tasks: {str(e)}"
        )


