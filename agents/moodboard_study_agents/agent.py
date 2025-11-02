"""
Study/Academic Stress Agent Configuration

Multi-agent system for analyzing voice journal sessions (study mode):
1. Parallel agents for summary and recommendations
2. Safety refinement loop with reviewer and refiner
3. MCP integration for saving results to Firebase

Environment: All configuration loaded from root backend .env file
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables FIRST - try .env.production (Cloud Run), then .env (local dev)
backend_root = Path(__file__).parent.parent.parent
env_production = backend_root / ".env.production"
env_file = backend_root / ".env"

if env_production.exists():
    load_dotenv(env_production)
    print(f"✅ Loaded .env.production from: {env_production}")
elif env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded .env from: {env_file}")
else:
    print("ℹ️  No .env file found, using system environment variables")

from .summary_agent import summary_agent
from .rec_agent import get_recommendation_agent  # Now a factory function that takes mcp_toolset
from .prompts import SAFETY_REVIEWER_PROMPT, SAFETY_REFINER_PROMPT
from .tools import exit_safety_loop, escalate_safety_concern
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent, LoopAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# MCP Server Path - Use wrapper script to avoid import issues
MCP_SERVER_PATH = str((Path(__file__).parent.parent / "mcp_server" / "run_server.py").resolve())

# Prepare environment variables for MCP server subprocess
# The subprocess inherits all environment variables from parent process
mcp_env = os.environ.copy()

# Ensure SERVICE_ACCOUNT_KEY_PATH is set (use from env or default path)
if not mcp_env.get("SERVICE_ACCOUNT_KEY_PATH"):
    # Default to backend root's firebase-service-account.json
    backend_root = Path(__file__).parent.parent.parent
    default_service_account = backend_root / "firebase-service-account.json"
    if default_service_account.exists():
        mcp_env["SERVICE_ACCOUNT_KEY_PATH"] = str(default_service_account.resolve())
        print(f"ℹ️  Using default Firebase credentials: {default_service_account}")

# Debug: Print environment status (only on first load)
print(f"🔧 MCP Environment Setup (Study Agents):")
print(f"   SERVICE_ACCOUNT_KEY_PATH: {'SET' if mcp_env.get('SERVICE_ACCOUNT_KEY_PATH') else '❌ NOT SET'}")
print(f"   GEMINI_API_KEY: {'SET' if mcp_env.get('GEMINI_API_KEY') else '❌ NOT SET'}")
print(f"   MODEL_NAME: {mcp_env.get('MODEL_NAME', 'NOT SET')}")

# Create MCP toolset (for Sahay ecosystem data access)
# ⚡ CRITICAL: 30s timeout for Firebase operations (saves take 5-10s)
mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[MCP_SERVER_PATH],
            env=mcp_env  # Pass complete environment to subprocess
        ),
        timeout=30.0  # Increased from default 5s to handle Firebase latency
    )
)

# Create recommendation agent with MCP toolset access
recommendation_agent = get_recommendation_agent(mcp_toolset)

parallel_study_stress_agent = ParallelAgent(
    name="parallel_study_stress_agent",
    sub_agents=[summary_agent, recommendation_agent],
    description="Runs multiple academic stress analysis agents in parallel"
)

# Get MODEL_NAME with fallback default
model_name = os.getenv("MODEL_NAME", "gemini-2.0-flash")
if not model_name or model_name.lower() == "none":
    model_name = "gemini-2.0-flash"

# Safety Reviewer - analyzes current state for academic stress management
safety_reviewer_agent = LlmAgent(
    model=model_name,
    name="safety_reviewer_agent",
    instruction=SAFETY_REVIEWER_PROMPT,
    output_key="safety_feedback"
)

# Safety Refiner - improves based on feedback or exits
safety_refiner_agent = LlmAgent(
    model=model_name,
    name="safety_refiner_agent",
    instruction=SAFETY_REFINER_PROMPT,
    tools=[mcp_toolset, exit_safety_loop, escalate_safety_concern],
    output_key="safety_guidelines"
)

# Safety Refinement Loop - iteratively improves safety until approved
safety_refinement_loop = LoopAgent(
    name="safety_refinement_loop",
    sub_agents=[safety_reviewer_agent, safety_refiner_agent],
    max_iterations=3,  # Prevent infinite loops
    description="Iteratively refines academic stress responses until safety criteria are met"
)

study_stress_agent = SequentialAgent(
    name="study_stress_agent",
    sub_agents=[parallel_study_stress_agent, safety_refinement_loop],
    description="Coordinates parallel academic stress analysis with iterative safety refinement."
)

root_agent = study_stress_agent
