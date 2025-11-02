from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables FIRST
backend_root = Path(__file__).parent.parent.parent.parent
env_production = backend_root / ".env.production"
env_file = backend_root / ".env"

if env_production.exists():
    load_dotenv(env_production)
elif env_file.exists():
    load_dotenv(env_file)

from .prompts import RECOMMENDATION_AGENT_PROMPT
from google.adk.agents import LlmAgent
from .tools import Mem0Tool

mem0_tool = Mem0Tool()

def get_recommendation_agent(mcp_toolset):
    """
    Factory function to create study recommendation agent with MCP toolset access.
    
    The agent has access to:
    - Mem0 tools (memory search/save)
    - MCP toolset (Eisenhower tasks, daily study data, stats, Pomodoro analytics)
    
    Args:
        mcp_toolset: MCPToolset instance with access to user study data
        
    Returns:
        LlmAgent configured for academic stress recommendations
    """
    # Get MODEL_NAME with fallback default
    model_name = os.getenv("MODEL_NAME", "gemini-2.0-flash")
    if not model_name or model_name.lower() == "none":
        model_name = "gemini-2.0-flash"
    
    return LlmAgent(
        model=model_name,
        name="recommendation_agent",
        instruction=RECOMMENDATION_AGENT_PROMPT,
        output_key="recommendation",
        tools=[mem0_tool.save_memory, mem0_tool.search_memory, mcp_toolset]
    )