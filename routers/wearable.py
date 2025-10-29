from fastapi import APIRouter, Response, status
from sqlmodel import select, func, and_
from datetime import datetime, date, timezone
from db import SessionDep
from model import (
    WearableDevice,
    WearableDeviceInput,
    WearableData,
    WearableDataInput,
    WearableInsights,
    WearableAnalysisRequest,
    WearableInsightsResponse,
    WearableDeviceType
)
from utils import TokenDep
import uuid
import random

router = APIRouter(tags=["Wearable"])


@router.post("/wearable/devices", status_code=status.HTTP_201_CREATED)
async def register_wearable_device(
    device_data: WearableDeviceInput, 
    token_data: TokenDep, 
    session: SessionDep
):
    """Register a new wearable device for the user"""
    try:
        # Check if device already exists
        existing_device = session.exec(
            select(WearableDevice)
            .where(WearableDevice.user_id == token_data.user_id)
            .where(WearableDevice.device_id == device_data.device_id)
        ).first()
        
        if existing_device:
            return Response(
                status_code=status.HTTP_409_CONFLICT,
                content="Device already registered"
            )
        
        new_device = WearableDevice(
            user_id=token_data.user_id,
            device_type=device_data.device_type,
            device_name=device_data.device_name,
            device_id=device_data.device_id,
            is_active=True
        )
        
        session.add(new_device)
        session.commit()
        session.refresh(new_device)
        
        return {
            "device_id": str(new_device.id),
            "device_name": new_device.device_name,
            "device_type": new_device.device_type,
            "status": "registered"
        }
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/wearable/devices")
async def get_user_devices(token_data: TokenDep, session: SessionDep):
    """Get all registered devices for the user"""
    try:
        devices = session.exec(
            select(WearableDevice)
            .where(WearableDevice.user_id == token_data.user_id)
            .where(WearableDevice.is_active == True)
        ).all()
        
        return [
            {
                "device_id": str(device.id),
                "device_name": device.device_name,
                "device_type": device.device_type,
                "is_active": device.is_active,
                "last_sync": device.last_sync.isoformat() if device.last_sync else None,
                "created_at": device.created_at.isoformat()
            }
            for device in devices
        ]
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.post("/wearable/data", status_code=status.HTTP_201_CREATED)
async def ingest_wearable_data(
    data: WearableDataInput, 
    token_data: TokenDep, 
    session: SessionDep
):
    """Ingest wearable data from devices/Health Connect"""
    try:
        # Parse date
        data_date = datetime.strptime(data.data_date, "%Y-%m-%d").date()
        
        # Find the device
        device = session.exec(
            select(WearableDevice)
            .where(WearableDevice.user_id == token_data.user_id)
            .where(WearableDevice.device_id == data.device_id)
        ).first()
        
        if not device:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Device not found"
            )
        
        # Check if data already exists for this date
        existing_data = session.exec(
            select(WearableData)
            .where(WearableData.user_id == token_data.user_id)
            .where(WearableData.device_id == device.id)
            .where(WearableData.data_date == data_date)
        ).first()
        
        if existing_data:
            # Update existing data
            for field, value in data.dict(exclude_unset=True).items():
                if field not in ['device_id', 'data_date']:
                    setattr(existing_data, field, value)
            
            session.add(existing_data)
            session.commit()
            return Response(status_code=status.HTTP_200_OK)
        
        # Create new data entry
        new_data = WearableData(
            user_id=token_data.user_id,
            device_id=device.id,
            data_date=data_date,
            **data.dict(exclude={'device_id', 'data_date'})
        )
        
        session.add(new_data)
        session.commit()
        session.refresh(new_data)
        
        return {
            "data_id": str(new_data.id),
            "data_date": new_data.data_date.isoformat(),
            "status": "created"
        }
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/wearable/data/{date}")
async def get_wearable_data_by_date(
    date: str, 
    token_data: TokenDep, 
    session: SessionDep
):
    """Get wearable data for a specific date"""
    try:
        data_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        wearable_data = session.exec(
            select(WearableData)
            .where(WearableData.user_id == token_data.user_id)
            .where(WearableData.data_date == data_date)
        ).first()
        
        if not wearable_data:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="No wearable data found for this date"
            )
        
        return {
            "data_id": str(wearable_data.id),
            "data_date": wearable_data.data_date.isoformat(),
            "sleep": {
                "duration_hours": wearable_data.sleep_duration_hours,
                "efficiency": wearable_data.sleep_efficiency,
                "deep_sleep_hours": wearable_data.deep_sleep_hours,
                "rem_sleep_hours": wearable_data.rem_sleep_hours,
                "light_sleep_hours": wearable_data.light_sleep_hours,
                "sleep_score": wearable_data.sleep_score,
                "bedtime": wearable_data.bedtime.isoformat() if wearable_data.bedtime else None,
                "wake_time": wearable_data.wake_time.isoformat() if wearable_data.wake_time else None,
            },
            "heart_rate": {
                "avg_heart_rate": wearable_data.avg_heart_rate,
                "resting_heart_rate": wearable_data.resting_heart_rate,
                "max_heart_rate": wearable_data.max_heart_rate,
                "hrv_rmssd": wearable_data.hrv_rmssd,
                "hrv_z_score": wearable_data.hrv_z_score,
            },
            "activity": {
                "steps": wearable_data.steps,
                "calories_burned": wearable_data.calories_burned,
                "active_minutes": wearable_data.active_minutes,
                "distance_km": wearable_data.distance_km,
                "floors_climbed": wearable_data.floors_climbed,
            },
            "stress_recovery": {
                "stress_score": wearable_data.stress_score,
                "stress_events": wearable_data.stress_events,
                "recovery_score": wearable_data.recovery_score,
                "energy_level": wearable_data.energy_level,
            },
            "environment": {
                "ambient_temperature": wearable_data.ambient_temperature,
                "humidity": wearable_data.humidity,
                "noise_level": wearable_data.noise_level,
                "light_level": wearable_data.light_level,
            },
            "additional": {
                "breathing_rate": wearable_data.breathing_rate,
                "blood_oxygen": wearable_data.blood_oxygen,
            },
            "raw_data": wearable_data.raw_data,
            "created_at": wearable_data.created_at.isoformat()
        }
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/wearable/insights/{date}")
async def get_wearable_insights(
    date: str, 
    token_data: TokenDep, 
    session: SessionDep
):
    """Get AI-generated insights for a specific date"""
    try:
        data_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        insights = session.exec(
            select(WearableInsights)
            .where(WearableInsights.user_id == token_data.user_id)
            .where(WearableInsights.insight_date == data_date)
        ).first()
        
        if not insights:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="No insights found for this date"
            )
        
        return {
            "insight_id": str(insights.id),
            "insight_date": insights.insight_date.isoformat(),
            "insight_type": insights.insight_type,
            "overall_recovery_score": insights.overall_recovery_score,
            "sleep_debt_hours": insights.sleep_debt_hours,
            "stress_level": insights.stress_level,
            "focus_recommendation": insights.focus_recommendation,
            "ai_insights": insights.ai_insights,
            "confidence_score": insights.confidence_score,
            "recommendations": {
                "focus_duration": insights.recommended_focus_duration,
                "break_duration": insights.recommended_break_duration,
                "activities": insights.recommended_activities,
            },
            "created_at": insights.created_at.isoformat()
        }
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/wearable/recovery-score")
async def get_current_recovery_score(token_data: TokenDep, session: SessionDep):
    """Get current recovery score based on latest data"""
    try:
        # Get latest wearable data
        latest_data = session.exec(
            select(WearableData)
            .where(WearableData.user_id == token_data.user_id)
            .order_by(WearableData.data_date.desc())
        ).first()
        
        if not latest_data:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="No wearable data available"
            )
        
        # Calculate recovery score based on available data
        recovery_score = calculate_recovery_score(latest_data)
        
        return {
            "recovery_score": recovery_score,
            "data_date": latest_data.data_date.isoformat(),
            "factors": {
                "sleep_quality": latest_data.sleep_score or 0,
                "hrv_score": latest_data.hrv_rmssd or 0,
                "stress_level": latest_data.stress_score or 0,
                "activity_level": latest_data.active_minutes or 0,
            },
            "recommendation": get_recovery_recommendation(recovery_score)
        }
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


# AI/MCP Integration Endpoints
@router.post("/wearable/ai/analyze")
async def analyze_wearable_data(
    analysis_request: WearableAnalysisRequest,
    token_data: TokenDep,
    session: SessionDep
):
    """Send wearable data to AI/MCP server for analysis"""
    try:
        data_date = datetime.strptime(analysis_request.data_date, "%Y-%m-%d").date()
        
        # Get wearable data for the date
        wearable_data = session.exec(
            select(WearableData)
            .where(WearableData.user_id == token_data.user_id)
            .where(WearableData.data_date == data_date)
        ).first()
        
        if not wearable_data:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="No wearable data found for analysis"
            )
        
        # Prepare data for AI analysis
        analysis_data = {
            "user_id": str(token_data.user_id),
            "data_date": analysis_request.data_date,
            "analysis_type": analysis_request.analysis_type,
            "wearable_data": {
                "sleep": {
                    "duration_hours": wearable_data.sleep_duration_hours,
                    "efficiency": wearable_data.sleep_efficiency,
                    "deep_sleep_hours": wearable_data.deep_sleep_hours,
                    "rem_sleep_hours": wearable_data.rem_sleep_hours,
                    "sleep_score": wearable_data.sleep_score,
                },
                "heart_rate": {
                    "avg_heart_rate": wearable_data.avg_heart_rate,
                    "resting_heart_rate": wearable_data.resting_heart_rate,
                    "hrv_rmssd": wearable_data.hrv_rmssd,
                    "hrv_z_score": wearable_data.hrv_z_score,
                },
                "activity": {
                    "steps": wearable_data.steps,
                    "active_minutes": wearable_data.active_minutes,
                    "calories_burned": wearable_data.calories_burned,
                },
                "stress": {
                    "stress_score": wearable_data.stress_score,
                    "stress_events": wearable_data.stress_events,
                    "energy_level": wearable_data.energy_level,
                },
                "environment": {
                    "noise_level": wearable_data.noise_level,
                    "light_level": wearable_data.light_level,
                    "temperature": wearable_data.ambient_temperature,
                }
            }
        }
        
        # TODO: Send to AI/MCP server
        # For now, generate mock AI insights
        ai_insights = generate_mock_ai_insights(analysis_data)
        
        # Store insights in database
        insights = WearableInsights(
            user_id=token_data.user_id,
            insight_date=data_date,
            insight_type=analysis_request.analysis_type,
            overall_recovery_score=ai_insights["recovery_score"],
            sleep_debt_hours=ai_insights["sleep_debt"],
            stress_level=ai_insights["stress_level"],
            focus_recommendation=ai_insights["focus_recommendation"],
            ai_insights=ai_insights["detailed_insights"],
            confidence_score=ai_insights["confidence"],
            recommended_focus_duration=ai_insights["focus_duration"],
            recommended_break_duration=ai_insights["break_duration"],
            recommended_activities=ai_insights["activities"]
        )
        
        session.add(insights)
        session.commit()
        session.refresh(insights)
        
        return {
            "analysis_id": str(insights.id),
            "analysis_type": analysis_request.analysis_type,
            "insights": ai_insights,
            "status": "completed"
        }
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/wearable/ai/recommendations")
async def get_ai_recommendations(
    token_data: TokenDep,
    session: SessionDep
):
    """Get AI-generated recommendations based on wearable data"""
    try:
        # Get latest insights
        latest_insights = session.exec(
            select(WearableInsights)
            .where(WearableInsights.user_id == token_data.user_id)
            .order_by(WearableInsights.insight_date.desc())
        ).first()
        
        if not latest_insights:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="No AI insights available"
            )
        
        return {
            "recommendations": {
                "focus_session_length": latest_insights.recommended_focus_duration,
                "break_duration": latest_insights.recommended_break_duration,
                "activities": latest_insights.recommended_activities,
                "environmental_suggestions": latest_insights.ai_insights.get("environmental", {}),
                "wellness_activities": latest_insights.ai_insights.get("wellness", {}),
            },
            "confidence_score": latest_insights.confidence_score,
            "insight_date": latest_insights.insight_date.isoformat()
        }
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


# Mock Data Generation for Development
@router.post("/wearable/mock-data/{date}")
async def generate_mock_wearable_data(
    date: str,
    token_data: TokenDep,
    session: SessionDep
):
    """Generate mock wearable data for development/testing"""
    try:
        data_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Create mock device if none exists
        mock_device = session.exec(
            select(WearableDevice)
            .where(WearableDevice.user_id == token_data.user_id)
            .where(WearableDevice.device_name.like("%Mock%"))
        ).first()
        
        if not mock_device:
            mock_device = WearableDevice(
                user_id=token_data.user_id,
                device_type=WearableDeviceType.SMART_WATCH,
                device_name="Mock Apple Watch Series 9",
                device_id="mock_device_001",
                is_active=True
            )
            session.add(mock_device)
            session.commit()
            session.refresh(mock_device)
        
        # Generate realistic mock data
        mock_data = WearableData(
            user_id=token_data.user_id,
            device_id=mock_device.id,
            data_date=data_date,
            
            # Sleep Data
            sleep_duration_hours=random.uniform(6.5, 8.5),
            sleep_efficiency=random.uniform(0.75, 0.95),
            deep_sleep_hours=random.uniform(1.5, 2.5),
            rem_sleep_hours=random.uniform(1.0, 2.0),
            light_sleep_hours=random.uniform(3.0, 5.0),
            sleep_score=random.randint(70, 95),
            
            # Heart Rate Data
            avg_heart_rate=random.randint(65, 85),
            resting_heart_rate=random.randint(55, 75),
            max_heart_rate=random.randint(180, 200),
            hrv_rmssd=random.uniform(25, 45),
            hrv_z_score=random.uniform(-1.5, 1.5),
            
            # Activity Data
            steps=random.randint(8000, 15000),
            calories_burned=random.randint(1800, 2500),
            active_minutes=random.randint(30, 90),
            distance_km=random.uniform(6.0, 12.0),
            floors_climbed=random.randint(5, 25),
            
            # Stress & Recovery
            stress_score=random.uniform(0.1, 0.8),
            stress_events=random.randint(0, 5),
            recovery_score=random.randint(60, 95),
            energy_level=random.choice(["low", "medium", "high"]),
            
            # Environmental Data
            ambient_temperature=random.uniform(20, 25),
            humidity=random.uniform(40, 60),
            noise_level=random.uniform(30, 70),
            light_level=random.choice(["low", "medium", "high"]),
            
            # Additional Metrics
            breathing_rate=random.uniform(12, 20),
            blood_oxygen=random.uniform(95, 99),
        )
        
        session.add(mock_data)
        session.commit()
        session.refresh(mock_data)
        
        return {
            "status": "mock_data_created",
            "data_id": str(mock_data.id),
            "data_date": mock_data.data_date.isoformat(),
            "device_name": mock_device.device_name
        }
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


# Helper Functions
def calculate_recovery_score(wearable_data):
    """Calculate recovery score based on wearable data"""
    score = 50  # Base score
    
    # Sleep quality contribution (30%)
    if wearable_data.sleep_score:
        score += (wearable_data.sleep_score - 50) * 0.3
    
    # HRV contribution (25%)
    if wearable_data.hrv_rmssd:
        if wearable_data.hrv_rmssd > 35:
            score += 15
        elif wearable_data.hrv_rmssd > 25:
            score += 5
    
    # Stress level contribution (25%)
    if wearable_data.stress_score:
        score -= wearable_data.stress_score * 30
    
    # Activity contribution (20%)
    if wearable_data.active_minutes:
        if wearable_data.active_minutes > 60:
            score += 10
        elif wearable_data.active_minutes > 30:
            score += 5
    
    return max(0, min(100, int(score)))


def get_recovery_recommendation(score):
    """Get recommendation based on recovery score"""
    if score >= 80:
        return "Excellent recovery! You're ready for high-intensity tasks."
    elif score >= 60:
        return "Good recovery. Moderate-intensity tasks recommended."
    elif score >= 40:
        return "Fair recovery. Light tasks and extra breaks recommended."
    else:
        return "Poor recovery. Focus on rest and light activities."


def generate_mock_ai_insights(analysis_data):
    """Generate mock AI insights for development"""
    return {
        "recovery_score": random.randint(60, 90),
        "sleep_debt": random.uniform(-2, 1),
        "stress_level": random.choice(["low", "medium", "high"]),
        "focus_recommendation": random.choice(["high", "medium", "low"]),
        "confidence": random.uniform(0.7, 0.95),
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
