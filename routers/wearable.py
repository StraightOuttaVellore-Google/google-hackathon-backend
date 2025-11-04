"""
Wearable Router - Firebase Version

Handles wearable device data using Firestore for real-time sync.
Includes Google Cloud IoT Core mock integration (non-breaking).
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime, date
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from typing import Optional, Dict, Any
import uuid
import random
import os

from firebase_db import get_firestore
from model import (
    WearableDeviceInput,
    WearableDataInput,
    WearableAnalysisRequest,
    WearableDeviceType
)
from utils import TokenDep

router = APIRouter(tags=["Wearable"])

# Google Cloud IoT Core configuration (mock/non-breaking)
IOT_CORE_ENABLED = os.getenv("IOT_CORE_ENABLED", "false").lower() == "true"
IOT_CORE_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
IOT_CORE_REGION = os.getenv("IOT_CORE_REGION", "us-central1")


def mock_iot_core_publish(device_id: str, data: Dict[str, Any]) -> bool:
    """
    Mock Google Cloud IoT Core publish function.
    In production, this would publish to IoT Core MQTT/HTTP bridge.
    """
    if not IOT_CORE_ENABLED:
        # Silent mock - just log that it would publish
        print(f"[IoT Core Mock] Would publish data for device {device_id}")
        return True
    
    try:
        # In real implementation, would use google-cloud-iot:
        # from google.cloud import iot_v1
        # client = iot_v1.DeviceManagerClient()
        # client.send_command_to_device(...)
        print(f"[IoT Core] Publishing data for device {device_id} (mock mode)")
        return True
    except Exception as e:
        print(f"[IoT Core] Error publishing (non-breaking): {e}")
        return False  # Non-breaking - returns False but doesn't fail request


@router.post("/wearable/devices", status_code=status.HTTP_201_CREATED)
async def register_wearable_device(
    device_data: WearableDeviceInput, 
    token_data: TokenDep
):
    """Register a new wearable device for the user"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Check if device already exists
        devices_ref = db.collection('wearable_devices')
        query = devices_ref.where('user_id', '==', user_id)\
                          .where('device_id', '==', device_data.device_id)\
                          .limit(1)
        
        existing_docs = list(query.stream())
        
        if existing_docs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Device already registered"
            )
        
        # Create new device
        device_id_doc = str(uuid.uuid4())
        device_data_dict = {
            "user_id": user_id,
            "device_type": device_data.device_type.value if hasattr(device_data.device_type, 'value') else str(device_data.device_type),
            "device_name": device_data.device_name,
            "device_id": device_data.device_id,
            "is_active": True,
            "created_at": SERVER_TIMESTAMP,
            "last_sync": None,
        }
        
        devices_ref.document(device_id_doc).set(device_data_dict)
        
        # Mock IoT Core registration
        mock_iot_core_publish(device_data.device_id, {"action": "register", "device_type": str(device_data.device_type)})
        
        return {
            "device_id": device_id_doc,
            "device_name": device_data.device_name,
            "device_type": device_data.device_type.value if hasattr(device_data.device_type, 'value') else str(device_data.device_type),
            "status": "registered"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering device: {str(e)}"
        )


@router.get("/wearable/devices")
async def get_user_devices(token_data: TokenDep):
    """Get all registered devices for the user"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        devices_ref = db.collection('wearable_devices')
        query = devices_ref.where('user_id', '==', user_id)\
                          .where('is_active', '==', True)
        
        devices = []
        for doc in query.stream():
            data = doc.to_dict()
            devices.append({
                "device_id": doc.id,
                "device_name": data.get('device_name', ''),
                "device_type": data.get('device_type', ''),
                "is_active": data.get('is_active', True),
                "last_sync": data.get('last_sync') if data.get('last_sync') else None,
                "created_at": data.get('created_at') if data.get('created_at') else None,
            })
        
        return devices
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving devices: {str(e)}"
        )


@router.post("/wearable/data", status_code=status.HTTP_201_CREATED)
async def ingest_wearable_data(
    data: WearableDataInput, 
    token_data: TokenDep
):
    """Ingest wearable data from devices/Health Connect"""
    try:
        # Parse date
        data_date = datetime.strptime(data.data_date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Find the device
        devices_ref = db.collection('wearable_devices')
        device_query = devices_ref.where('user_id', '==', user_id)\
                                  .where('device_id', '==', data.device_id)\
                                  .limit(1)
        
        device_docs = list(device_query.stream())
        if not device_docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        device_id_doc = device_docs[0].id
        
        # Check if data already exists for this date
        wearable_data_ref = db.collection('wearable_data')
        existing_query = wearable_data_ref.where('user_id', '==', user_id)\
                                          .where('device_id', '==', device_id_doc)\
                                          .where('data_date', '==', data_date)\
                                          .limit(1)
        
        existing_docs = list(existing_query.stream())
        
        # Prepare data dict (exclude device_id and data_date from input)
        data_dict = data.model_dump(exclude={'device_id', 'data_date'})
        data_dict.update({
            "user_id": user_id,
            "device_id": device_id_doc,
            "data_date": data_date,
            "updated_at": SERVER_TIMESTAMP,
        })
        
        if existing_docs:
            # Update existing data
            existing_docs[0].reference.update(data_dict)
            data_id = existing_docs[0].id
            status_code = status.HTTP_200_OK
        else:
            # Create new data entry
            data_dict["created_at"] = SERVER_TIMESTAMP
            data_id = str(uuid.uuid4())
            wearable_data_ref.document(data_id).set(data_dict)
            status_code = status.HTTP_201_CREATED
        
        # Update device last_sync
        device_docs[0].reference.update({"last_sync": SERVER_TIMESTAMP})
        
        # Mock IoT Core publish
        mock_iot_core_publish(data.device_id, {"action": "data_ingest", "data_date": data_date})
        
        return {
            "data_id": data_id,
            "data_date": data_date,
            "status": "created" if status_code == status.HTTP_201_CREATED else "updated"
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
            detail=f"Error ingesting wearable data: {str(e)}"
        )


@router.get("/wearable/data/{date}")
async def get_wearable_data_by_date(
    date: str, 
    token_data: TokenDep
):
    """Get wearable data for a specific date"""
    try:
        data_date = datetime.strptime(date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        wearable_data_ref = db.collection('wearable_data')
        query = wearable_data_ref.where('user_id', '==', user_id)\
                                 .where('data_date', '==', data_date)\
                                 .limit(1)
        
        docs = list(query.stream())
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No wearable data found for this date"
            )
        
        data = docs[0].to_dict()
        
        return {
            "data_id": docs[0].id,
            "data_date": data.get('data_date'),
            "sleep": {
                "duration_hours": data.get('sleep_duration_hours'),
                "efficiency": data.get('sleep_efficiency'),
                "deep_sleep_hours": data.get('deep_sleep_hours'),
                "rem_sleep_hours": data.get('rem_sleep_hours'),
                "light_sleep_hours": data.get('light_sleep_hours'),
                "sleep_score": data.get('sleep_score'),
                "bedtime": data.get('bedtime'),
                "wake_time": data.get('wake_time'),
            },
            "heart_rate": {
                "avg_heart_rate": data.get('avg_heart_rate'),
                "resting_heart_rate": data.get('resting_heart_rate'),
                "max_heart_rate": data.get('max_heart_rate'),
                "hrv_rmssd": data.get('hrv_rmssd'),
                "hrv_z_score": data.get('hrv_z_score'),
            },
            "activity": {
                "steps": data.get('steps'),
                "calories_burned": data.get('calories_burned'),
                "active_minutes": data.get('active_minutes'),
                "distance_km": data.get('distance_km'),
                "floors_climbed": data.get('floors_climbed'),
            },
            "stress_recovery": {
                "stress_score": data.get('stress_score'),
                "stress_events": data.get('stress_events'),
                "recovery_score": data.get('recovery_score'),
                "energy_level": data.get('energy_level'),
            },
            "environment": {
                "ambient_temperature": data.get('ambient_temperature'),
                "humidity": data.get('humidity'),
                "noise_level": data.get('noise_level'),
                "light_level": data.get('light_level'),
            },
            "additional": {
                "breathing_rate": data.get('breathing_rate'),
                "blood_oxygen": data.get('blood_oxygen'),
            },
            "raw_data": data.get('raw_data'),
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
            detail=f"Error retrieving wearable data: {str(e)}"
        )


@router.get("/wearable/insights/{date}")
async def get_wearable_insights(
    date: str, 
    token_data: TokenDep
):
    """Get AI-generated insights for a specific date"""
    try:
        data_date = datetime.strptime(date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        insights_ref = db.collection('wearable_insights')
        query = insights_ref.where('user_id', '==', user_id)\
                           .where('insight_date', '==', data_date)\
                           .limit(1)
        
        docs = list(query.stream())
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No insights found for this date"
            )
        
        data = docs[0].to_dict()
        
        return {
            "insight_id": docs[0].id,
            "insight_date": data.get('insight_date'),
            "insight_type": data.get('insight_type'),
            "overall_recovery_score": data.get('overall_recovery_score'),
            "sleep_debt_hours": data.get('sleep_debt_hours'),
            "stress_level": data.get('stress_level'),
            "focus_recommendation": data.get('focus_recommendation'),
            "ai_insights": data.get('ai_insights'),
            "confidence_score": data.get('confidence_score'),
            "recommendations": {
                "focus_duration": data.get('recommended_focus_duration'),
                "break_duration": data.get('recommended_break_duration'),
                "activities": data.get('recommended_activities'),
            },
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
            detail=f"Error retrieving insights: {str(e)}"
        )


@router.get("/wearable/recovery-score")
async def get_current_recovery_score(token_data: TokenDep):
    """Get current recovery score based on latest data"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Get latest wearable data
        wearable_data_ref = db.collection('wearable_data')
        query = wearable_data_ref.where('user_id', '==', user_id)\
                                 .order_by('data_date', direction='DESCENDING')\
                                 .limit(1)
        
        docs = list(query.stream())
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No wearable data available"
            )
        
        data = docs[0].to_dict()
        
        # Calculate recovery score
        recovery_score = calculate_recovery_score(data)
        
        return {
            "recovery_score": recovery_score,
            "data_date": data.get('data_date'),
            "factors": {
                "sleep_quality": data.get('sleep_score') or 0,
                "hrv_score": data.get('hrv_rmssd') or 0,
                "stress_level": data.get('stress_score') or 0,
                "activity_level": data.get('active_minutes') or 0,
            },
            "recommendation": get_recovery_recommendation(recovery_score)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating recovery score: {str(e)}"
        )


@router.post("/wearable/ai/analyze")
async def analyze_wearable_data(
    analysis_request: WearableAnalysisRequest,
    token_data: TokenDep
):
    """Send wearable data to AI/MCP server for analysis"""
    try:
        data_date = datetime.strptime(analysis_request.data_date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Get wearable data for the date
        wearable_data_ref = db.collection('wearable_data')
        query = wearable_data_ref.where('user_id', '==', user_id)\
                                 .where('data_date', '==', data_date)\
                                 .limit(1)
        
        docs = list(query.stream())
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No wearable data found for analysis"
            )
        
        data = docs[0].to_dict()
        
        # Prepare data for AI analysis
        analysis_data = {
            "user_id": user_id,
            "data_date": analysis_request.data_date,
            "analysis_type": analysis_request.analysis_type.value if hasattr(analysis_request.analysis_type, 'value') else str(analysis_request.analysis_type),
            "wearable_data": {
                "sleep": {
                    "duration_hours": data.get('sleep_duration_hours'),
                    "efficiency": data.get('sleep_efficiency'),
                    "deep_sleep_hours": data.get('deep_sleep_hours'),
                    "rem_sleep_hours": data.get('rem_sleep_hours'),
                    "sleep_score": data.get('sleep_score'),
                },
                "heart_rate": {
                    "avg_heart_rate": data.get('avg_heart_rate'),
                    "resting_heart_rate": data.get('resting_heart_rate'),
                    "hrv_rmssd": data.get('hrv_rmssd'),
                    "hrv_z_score": data.get('hrv_z_score'),
                },
                "activity": {
                    "steps": data.get('steps'),
                    "active_minutes": data.get('active_minutes'),
                    "calories_burned": data.get('calories_burned'),
                },
                "stress": {
                    "stress_score": data.get('stress_score'),
                    "stress_events": data.get('stress_events'),
                    "energy_level": data.get('energy_level'),
                },
                "environment": {
                    "noise_level": data.get('noise_level'),
                    "light_level": data.get('light_level'),
                    "temperature": data.get('ambient_temperature'),
                }
            }
        }
        
        # Generate mock AI insights (can be replaced with real AI call)
        ai_insights = generate_mock_ai_insights(analysis_data)
        
        # Store insights in database
        insights_ref = db.collection('wearable_insights')
        insight_id = str(uuid.uuid4())
        
        insight_data = {
            "user_id": user_id,
            "insight_date": data_date,
            "insight_type": analysis_request.analysis_type.value if hasattr(analysis_request.analysis_type, 'value') else str(analysis_request.analysis_type),
            "overall_recovery_score": ai_insights["recovery_score"],
            "sleep_debt_hours": ai_insights["sleep_debt"],
            "stress_level": ai_insights["stress_level"],
            "focus_recommendation": ai_insights["focus_recommendation"],
            "ai_insights": ai_insights["detailed_insights"],
            "confidence_score": ai_insights["confidence"],
            "recommended_focus_duration": ai_insights["focus_duration"],
            "recommended_break_duration": ai_insights["break_duration"],
            "recommended_activities": ai_insights["activities"],
            "created_at": SERVER_TIMESTAMP,
        }
        
        insights_ref.document(insight_id).set(insight_data)
        
        # Mock IoT Core publish for AI analysis
        mock_iot_core_publish(user_id, {"action": "ai_analysis", "analysis_type": str(analysis_request.analysis_type)})
        
        return {
            "analysis_id": insight_id,
            "analysis_type": analysis_request.analysis_type.value if hasattr(analysis_request.analysis_type, 'value') else str(analysis_request.analysis_type),
            "insights": ai_insights,
            "status": "completed"
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
            detail=f"Error analyzing wearable data: {str(e)}"
        )


@router.get("/wearable/ai/recommendations")
async def get_ai_recommendations(token_data: TokenDep):
    """Get AI-generated recommendations based on wearable data"""
    try:
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Get latest insights
        insights_ref = db.collection('wearable_insights')
        query = insights_ref.where('user_id', '==', user_id)\
                           .order_by('insight_date', direction='DESCENDING')\
                           .limit(1)
        
        docs = list(query.stream())
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No AI insights available"
            )
        
        data = docs[0].to_dict()
        ai_insights = data.get('ai_insights', {})
        
        return {
            "recommendations": {
                "focus_session_length": data.get('recommended_focus_duration'),
                "break_duration": data.get('recommended_break_duration'),
                "activities": data.get('recommended_activities'),
                "environmental_suggestions": ai_insights.get("environmental", {}),
                "wellness_activities": ai_insights.get("wellness", {}),
            },
            "confidence_score": data.get('confidence_score'),
            "insight_date": data.get('insight_date'),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving recommendations: {str(e)}"
        )


@router.post("/wearable/mock-data/{date}")
async def generate_mock_wearable_data(
    date: str,
    token_data: TokenDep
):
    """Generate mock wearable data for development/testing"""
    try:
        data_date = datetime.strptime(date, "%Y-%m-%d").date().isoformat()
        
        db = get_firestore()
        user_id = str(token_data.user_id)
        
        # Create mock device if none exists
        devices_ref = db.collection('wearable_devices')
        mock_device_query = devices_ref.where('user_id', '==', user_id)\
                                      .where('device_name', '>=', 'Mock')\
                                      .where('device_name', '<=', 'Mock\uf8ff')\
                                      .limit(1)
        
        mock_device_docs = list(mock_device_query.stream())
        
        if not mock_device_docs:
            # Create mock device
            device_id_doc = str(uuid.uuid4())
            devices_ref.document(device_id_doc).set({
                "user_id": user_id,
                "device_type": "SMART_WATCH",
                "device_name": "Mock Apple Watch Series 9",
                "device_id": "mock_device_001",
                "is_active": True,
                "created_at": SERVER_TIMESTAMP,
            })
            device_id_firestore = device_id_doc
        else:
            device_id_firestore = mock_device_docs[0].id
        
        # Generate realistic mock data
        wearable_data_ref = db.collection('wearable_data')
        data_id = str(uuid.uuid4())
        
        mock_data = {
            "user_id": user_id,
            "device_id": device_id_firestore,
            "data_date": data_date,
            
            # Sleep Data
            "sleep_duration_hours": round(random.uniform(6.5, 8.5), 2),
            "sleep_efficiency": round(random.uniform(0.75, 0.95), 2),
            "deep_sleep_hours": round(random.uniform(1.5, 2.5), 2),
            "rem_sleep_hours": round(random.uniform(1.0, 2.0), 2),
            "light_sleep_hours": round(random.uniform(3.0, 5.0), 2),
            "sleep_score": random.randint(70, 95),
            
            # Heart Rate Data
            "avg_heart_rate": random.randint(65, 85),
            "resting_heart_rate": random.randint(55, 75),
            "max_heart_rate": random.randint(180, 200),
            "hrv_rmssd": round(random.uniform(25, 45), 2),
            "hrv_z_score": round(random.uniform(-1.5, 1.5), 2),
            
            # Activity Data
            "steps": random.randint(8000, 15000),
            "calories_burned": random.randint(1800, 2500),
            "active_minutes": random.randint(30, 90),
            "distance_km": round(random.uniform(6.0, 12.0), 2),
            "floors_climbed": random.randint(5, 25),
            
            # Stress & Recovery
            "stress_score": round(random.uniform(0.1, 0.8), 2),
            "stress_events": random.randint(0, 5),
            "recovery_score": random.randint(60, 95),
            "energy_level": random.choice(["low", "medium", "high"]),
            
            # Environmental Data
            "ambient_temperature": round(random.uniform(20, 25), 2),
            "humidity": round(random.uniform(40, 60), 2),
            "noise_level": round(random.uniform(30, 70), 2),
            "light_level": random.choice(["low", "medium", "high"]),
            
            # Additional Metrics
            "breathing_rate": round(random.uniform(12, 20), 2),
            "blood_oxygen": round(random.uniform(95, 99), 2),
            
            "created_at": SERVER_TIMESTAMP,
        }
        
        wearable_data_ref.document(data_id).set(mock_data)
        
        # Mock IoT Core publish
        mock_iot_core_publish("mock_device_001", {"action": "mock_data_generated", "date": data_date})
        
        return {
            "status": "mock_data_created",
            "data_id": data_id,
            "data_date": data_date,
            "device_name": "Mock Apple Watch Series 9"
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating mock data: {str(e)}"
        )


# Helper Functions
def calculate_recovery_score(wearable_data: Dict[str, Any]) -> int:
    """Calculate recovery score based on wearable data"""
    score = 50  # Base score
    
    # Sleep quality contribution (30%)
    sleep_score = wearable_data.get('sleep_score')
    if sleep_score:
        score += (sleep_score - 50) * 0.3
    
    # HRV contribution (25%)
    hrv_rmssd = wearable_data.get('hrv_rmssd')
    if hrv_rmssd:
        if hrv_rmssd > 35:
            score += 15
        elif hrv_rmssd > 25:
            score += 5
    
    # Stress level contribution (25%)
    stress_score = wearable_data.get('stress_score')
    if stress_score:
        score -= stress_score * 30
    
    # Activity contribution (20%)
    active_minutes = wearable_data.get('active_minutes')
    if active_minutes:
        if active_minutes > 60:
            score += 10
        elif active_minutes > 30:
            score += 5
    
    return max(0, min(100, int(score)))


def get_recovery_recommendation(score: int) -> str:
    """Get recommendation based on recovery score"""
    if score >= 80:
        return "Excellent recovery! You're ready for high-intensity tasks."
    elif score >= 60:
        return "Good recovery. Moderate-intensity tasks recommended."
    elif score >= 40:
        return "Fair recovery. Light tasks and extra breaks recommended."
    else:
        return "Poor recovery. Focus on rest and light activities."


def generate_mock_ai_insights(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate mock AI insights for development"""
    return {
        "recovery_score": random.randint(60, 90),
        "sleep_debt": round(random.uniform(-2, 1), 2),
        "stress_level": random.choice(["low", "medium", "high"]),
        "focus_recommendation": random.choice(["high", "medium", "low"]),
        "confidence": round(random.uniform(0.7, 0.95), 2),
        "focus_duration": random.randint(20, 45),
        "break_duration": random.randint(5, 15),
        "detailed_insights": {
            "sleep_analysis": "Sleep quality is optimal for cognitive performance",
            "stress_indicators": "Stress levels are within normal range",
            "activity_assessment": "Activity levels support good recovery",
            "environmental": {
                "noise_recommendation": "Consider noise-canceling for focus",
                "lighting_suggestion": "Natural lighting optimal for productivity"
            },
            "wellness": {
                "breathing_exercises": "5-minute breathing session recommended",
                "movement_break": "Take a 10-minute walk"
            }
        },
        "activities": {
            "focus_activities": ["Deep work", "Study sessions", "Creative tasks"],
            "break_activities": ["Walking", "Stretching", "Hydration"],
            "wellness_activities": ["Meditation", "Breathing exercises", "Light movement"]
        }
    }
