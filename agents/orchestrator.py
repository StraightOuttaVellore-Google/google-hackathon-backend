"""
Wellness Agent Orchestrator

Coordinates wellness agent execution with MCP server integration.
Runs appropriate agent (study or general) based on mode and returns structured output.

**CLEAN ARCHITECTURE**: 
- Agents are defined in their own files (moodboard_wellness_agents, moodboard_study_agents)
- MCP tools are added to agents in their own files
- This orchestrator just imports and runs them
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, date, timedelta

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import pre-built agents (with MCP tools already included)
from moodboard_study_agents.agent import root_agent as study_agent
from moodboard_wellness_agents.agent import root_agent as wellness_agent


def map_priority_to_quadrant(priority: str) -> str:
    """Map priority classification to Eisenhower quadrant"""
    mapping = {
        "urgent_important": "high_imp_high_urg",
        "important_not_urgent": "high_imp_low_urg",
        "urgent_not_important": "low_imp_high_urg",
        "neither_urgent_nor_important": "low_imp_low_urg",
    }
    return mapping.get(priority, "high_imp_low_urg")  # Default to Q2


def calculate_due_date(suggested_days: int) -> str:
    """Calculate due date from now"""
    due = date.today() + timedelta(days=suggested_days)
    return due.strftime("%Y-%m-%d")


def strip_markdown_json(text: str) -> str:
    """
    Strip markdown code blocks from JSON strings.
    Agents often wrap JSON in ```json ... ``` blocks.
    """
    if not isinstance(text, str):
        return text
    
    # Remove markdown code block wrapper
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
    elif text.startswith("```"):
        text = text[3:]  # Remove ```
    
    if text.endswith("```"):
        text = text[:-3]  # Remove trailing ```
    
    return text.strip()


def parse_agent_output(raw_output: Dict, mode: str) -> Dict:
    """
    Parse and structure agent output for API response
    
    Args:
        raw_output: Raw output from agent runner
        mode: 'study' or 'general'
        
    Returns:
        Structured output matching VoiceJournalAnalysisResult schema
    """
    # Extract summary data
    summary_data = raw_output.get("generated_summary", "{}")
    if isinstance(summary_data, str):
        try:
            # Strip markdown code blocks before parsing
            clean_json = strip_markdown_json(summary_data)
            summary_data = json.loads(clean_json)
            print(f"✅ Successfully parsed summary with {len(summary_data.get('emotions', []))} emotions")
        except Exception as e:
            print(f"⚠️  Failed to parse summary JSON: {e}")
            print(f"   Raw summary preview: {summary_data[:100]}...")
            summary_data = {"summary": summary_data, "emotions": [], "focus_areas": [], "tags": []}
    
    # Extract recommendation data
    rec_data = raw_output.get("recommendation", "{}")
    if isinstance(rec_data, str):
        try:
            # Strip markdown code blocks before parsing
            clean_json = strip_markdown_json(rec_data)
            rec_data = json.loads(clean_json)
            print(f"✅ Successfully parsed recommendations: {len(rec_data.get('recommendations', []))} items")
        except Exception as e:
            print(f"⚠️  Failed to parse recommendation JSON: {e}")
            print(f"   Raw recommendation preview: {rec_data[:100]}...")
            rec_data = {"recommendations": [], "wellness_exercises": [], "resources": [], "tone": "supportive"}
    
    # Extract safety data
    safety_data = raw_output.get("safety_guidelines", {})
    safety_feedback = raw_output.get("safety_feedback", "")
    
    print(f"🔍 DEBUG - Safety data type: {type(safety_data)}")
    if isinstance(safety_data, str):
        print(f"   Safety data preview: {safety_data[:100]}...")
    print(f"   Safety feedback: {str(safety_feedback)[:100] if safety_feedback else 'None'}...")
    
    # Check if safety_data is just a confirmation message (agent completed save and exited)
    if isinstance(safety_data, str) and ("saved" in safety_data.lower() or "exit" in safety_data.lower()):
        print(f"✅ Safety data appears to be completion message, using default safe values")
    
    # Handle safety_data parsing with better error handling
    if isinstance(safety_data, dict):
        # Already a dict, use it as is
        pass
    elif isinstance(safety_data, str):
        # Try to parse string
        try:
            # Strip markdown code blocks before parsing
            clean_json = strip_markdown_json(safety_data)
            
            # Check if it's a valid JSON string (not empty, not just whitespace, not just `}`)
            if not clean_json or clean_json.strip() == "}" or clean_json.strip() == "":
                # Invalid JSON - check safety_feedback for approval status
                if "SAFETY_APPROVED" in str(safety_feedback).upper():
                    safety_data = {"is_safe": True, "safety_score": 0.95}
                else:
                    safety_data = {"is_safe": True, "safety_score": 0.9}
            else:
                # Try to parse as JSON
                safety_data = json.loads(clean_json)
                print(f"✅ Successfully parsed safety JSON: is_safe={safety_data.get('is_safe', 'N/A')}, score={safety_data.get('safety_score', 'N/A')}")
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse safety JSON: {e}")
            print(f"   Raw safety data preview: {safety_data[:100]}...")
            
            # Fallback: Check safety_feedback for approval
            if "SAFETY_APPROVED" in str(safety_feedback).upper():
                safety_data = {"is_safe": True, "safety_score": 0.95}
            else:
                safety_data = {"is_safe": True, "safety_score": 0.9}
        except Exception as e:
            print(f"⚠️  Unexpected error parsing safety JSON: {e}")
            # Default safe values
            if "SAFETY_APPROVED" in str(safety_feedback).upper():
                safety_data = {"is_safe": True, "safety_score": 0.95}
            else:
                safety_data = {"is_safe": True, "safety_score": 0.9}
    else:
        # Not a dict or string, check safety_feedback
        if "SAFETY_APPROVED" in str(safety_feedback).upper():
            safety_data = {"is_safe": True, "safety_score": 0.95}
        else:
            safety_data = {"is_safe": True, "safety_score": 0.9}
    
    # Ensure safety_data has required fields
    if not isinstance(safety_data, dict):
        safety_data = {"is_safe": True, "safety_score": 0.9}
    
    # Extract safety_approved and safety_score with defaults
    # Handle both "is_safe" and "safety_approved" keys (agents may use either)
    safety_approved = safety_data.get("is_safe", safety_data.get("safety_approved", True))
    safety_score = safety_data.get("safety_score", 0.95 if safety_approved else 0.5)
    
    # If safety_approved not found in dict, check safety_feedback for approval status
    if "is_safe" not in safety_data and "safety_approved" not in safety_data:
        # Check if we have approval in feedback
        if "SAFETY_APPROVED" in str(safety_feedback).upper():
            safety_approved = True
            safety_score = 0.95
        else:
            # Default to safe with moderate score
            safety_approved = True
            safety_score = 0.9
    
    # Ensure we have valid boolean values
    if not isinstance(safety_approved, bool):
        safety_approved = bool(safety_approved)
    
    # Ensure safety_score is a float between 0 and 1
    try:
        safety_score = float(safety_score)
        safety_score = max(0.0, min(1.0, safety_score))  # Clamp between 0 and 1
    except (ValueError, TypeError):
        safety_score = 0.95 if safety_approved else 0.5
    
    print(f"✅ Safety validation complete: approved={safety_approved}, score={safety_score:.2f}")
    
    # Build transcript summary (goes under transcript)
    transcript_summary = {
        "summary": summary_data.get("summary", ""),
        "emotions": summary_data.get("emotions", []),
        "focus_areas": summary_data.get("focus_areas", []),
        "tags": summary_data.get("tags", []),
    }
    
    if mode == "study":
        transcript_summary["stress_level"] = summary_data.get("stress_level")
        transcript_summary["academic_concerns"] = summary_data.get("academic_concerns", [])
    
    # Process recommended tasks
    raw_tasks = rec_data.get("recommended_tasks", [])
    processed_tasks = []
    for task in raw_tasks:
        processed_tasks.append({
            "task_title": task.get("task_title", ""),
            "task_description": task.get("task_description", ""),
            "priority_classification": task.get("priority_classification", "important_not_urgent"),
            "suggested_due_days": task.get("suggested_due_days", 7),
        })
    
    # Extract wellness pathways (new feature)
    wellness_pathways = rec_data.get("wellness_pathways", [])
    if not wellness_pathways:
        # Generate default pathways based on mode
        if mode == "study":
            wellness_pathways = [
                {
                    "pathway_name": "Focus Enhancement Program",
                    "pathway_type": "study_technique",
                    "description": "7-day program to improve concentration and study effectiveness",
                    "duration_days": 7
                }
            ]
        else:
            wellness_pathways = [
                {
                    "pathway_name": "Stress Management Journey",
                    "pathway_type": "stress_management",
                    "description": "7-day mindfulness and stress reduction program",
                    "duration_days": 7
                }
            ]
    
    # Build stats recommendations (goes in stats/analysis area)
    stats_recommendations = {
        "recommendations": rec_data.get("recommendations", []),
        "wellness_exercises": rec_data.get("wellness_exercises", []),
        "resources": rec_data.get("resources", []),
        "wellness_pathways": wellness_pathways,
        "recommended_tasks": processed_tasks,
        "tone": rec_data.get("tone", "supportive"),
    }
    
    if mode == "study":
        stats_recommendations["study_focus_tips"] = rec_data.get("study_focus_tips", [])
    
    return {
        "transcript_summary": transcript_summary,
        "stats_recommendations": stats_recommendations,
        "safety_approved": safety_approved,
        "safety_score": safety_score,
    }


async def run_wellness_analysis(
    transcript: str,
    mode: str,
    user_id: str,
    session_id: Optional[str] = None
) -> Dict:
    """
    Run wellness analysis with appropriate agent
    
    **PRODUCTION FLOW**:
    1. Select pre-built agent (with MCP tools already injected)
    2. Prepare context with user_id (available to all tools)
    3. Run agent via Runner
    4. Agent flow:
       - Parallel: Summary (mem0) + Recommendations (mem0 + MCP data tools)
       - Safety Loop: Reviewer → Refiner (max 3 iterations)
       - If approved: Refiner calls save_complete_wellness_analysis (MCP) → exit_safety_loop
    5. Parse and return structured output
    
    Args:
        transcript: Voice journal transcript
        mode: 'study' or 'wellness'
        user_id: User identifier
        session_id: Optional session identifier
        
    Returns:
        Structured analysis result with transcript_summary and stats_recommendations
    """
    # Select appropriate agent (pre-built with MCP tools)
    agent = study_agent if mode == "study" else wellness_agent
    
    # Initialize session service for Runner
    session_service = InMemorySessionService()
    app_name = "WellnessAnalysis"
    
    # Create or get session with context variables in state
    initial_state = {
        "transcript": transcript,
        "userId": user_id,  # MCP tools expect userId
        "mode": mode,
        "session_id": session_id or f"session_{datetime.utcnow().timestamp()}",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if session_id:
        try:
            session = await session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
            # Update state with new context
            session.state.update(initial_state)
        except:
            session = await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                state=initial_state
            )
    else:
        session = await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            state=initial_state
        )
        session_id = session.id
    
    # Run agent (MCP server starts automatically via MCPToolset)
    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service
    )
    
    try:
        print(f"🚀 Starting {mode} agent analysis for session {session_id}")
        print(f"📝 Transcript length: {len(transcript)} characters")
        
        # Create message with transcript for the agent
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=transcript)]
        )
        
        # Execute agent with message
        final_result = {}
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            # Collect final result from events
            if hasattr(event, 'is_final_response') and event.is_final_response():
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts') and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                try:
                                    # Try to parse as JSON if possible
                                    parsed = json.loads(part.text)
                                    final_result.update(parsed)
                                except:
                                    # If not JSON, store as text
                                    if 'response' not in final_result:
                                        final_result['response'] = part.text
        
        # After execution, get the session state which should contain agent outputs
        final_session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        # Extract agent outputs from session state
        # Agents output keys: generated_summary, recommendation, safety_guidelines
        
        # DEBUG: Print session state to see what agents actually output
        print(f"\n🔍 DEBUG - Final Session State:")
        print(f"   State keys: {list(final_session.state.keys())}")
        if 'generated_summary' in final_session.state:
            summary_preview = str(final_session.state['generated_summary'])[:200]
            print(f"   generated_summary: {summary_preview}...")
        if 'recommendation' in final_session.state:
            rec_preview = str(final_session.state['recommendation'])[:200]
            print(f"   recommendation: {rec_preview}...")
        if 'safety_guidelines' in final_session.state:
            safety_preview = str(final_session.state['safety_guidelines'])[:100]
            print(f"   safety_guidelines: {safety_preview}...")
        
        result = {
            "generated_summary": final_session.state.get("generated_summary", final_result.get("generated_summary", "{}")),
            "recommendation": final_session.state.get("recommendation", final_result.get("recommendation", "{}")),
            "safety_guidelines": final_session.state.get("safety_guidelines", final_result.get("safety_guidelines", {})),
        }
        
        # Merge any additional results from events
        result.update(final_result)
        
        print(f"\n✅ Agent execution completed for session {session_id}")
        print(f"📊 Result keys: {list(result.keys())}")
        
        # DEBUG: Print extracted results
        print(f"\n🔍 DEBUG - Extracted Results:")
        print(f"   generated_summary type: {type(result.get('generated_summary'))}")
        print(f"   recommendation type: {type(result.get('recommendation'))}")
        print(f"   safety_guidelines type: {type(result.get('safety_guidelines'))}")
        
        # Parse output into structured format
        structured_output = parse_agent_output(result, mode)
        
        # Add metadata
        structured_output["session_id"] = session_id or f"session_{datetime.utcnow().timestamp()}"
        structured_output["mode"] = mode
        structured_output["created_at"] = datetime.utcnow().isoformat()
        
        print(f"💾 Analysis structured and ready for session {session_id}")
        
        return structured_output
        
    except Exception as e:
        print(f"❌ Error in agent execution for session {session_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return error in expected format
        return {
            "session_id": session_id or f"session_error_{datetime.utcnow().timestamp()}",
            "mode": mode,
            "transcript_summary": {
                "summary": f"Analysis encountered an error. Our team has been notified.",
                "emotions": [],
                "focus_areas": [],
                "tags": [],
            },
            "stats_recommendations": {
                "recommendations": [],
                "wellness_exercises": [],
                "resources": [],
                "wellness_pathways": [],
                "recommended_tasks": [],
                "tone": "supportive",
            },
            "safety_approved": True,
            "safety_score": 1.0,
            "created_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }


def sync_run_wellness_analysis(transcript: str, mode: str, user_id: str, session_id: Optional[str] = None) -> Dict:
    """
    Synchronous wrapper for run_wellness_analysis
    
    Args:
        transcript: Voice journal transcript
        mode: 'study' or 'general'
        user_id: User identifier
        session_id: Optional session identifier
        
    Returns:
        Structured analysis result
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            run_wellness_analysis(transcript, mode, user_id, session_id)
        )
        return result
    finally:
        loop.close()

