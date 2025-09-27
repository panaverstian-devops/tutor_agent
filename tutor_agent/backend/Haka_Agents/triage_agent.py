import asyncio
import os
import sys
from dotenv import load_dotenv
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, Runner, ModelSettings, SQLiteSession, set_tracing_disabled, set_tracing_export_api_key, trace
from agents.mcp import MCPServerStreamableHttp

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PROMPTS.triage_prompt import Triage_Agent_Prompt

# Load environment variables
load_dotenv()

# Set up tracing with API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    set_tracing_export_api_key(OPENAI_API_KEY)

# Enable tracing for workflow monitoring
set_tracing_disabled(False)

# Create API provider
Provider = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Set up the chat completion model
model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=Provider,
)

# Local MCP Server Configuration for Student Data and Content
LOCAL_MCP_SERVER_URL = os.getenv("LOCAL_MCP_SERVER_URL", "http://localhost:8000/mcp")

def create_triage_agent():
    """Create and return the Triage Agent"""
    return Agent(
        name="Olivia", 
        instructions=Triage_Agent_Prompt,
        model=model,
        model_settings=ModelSettings(temperature=0.7),
    )

async def main():
    # Set up local MCP server parameters
    local_mcp_params = {
        "url": LOCAL_MCP_SERVER_URL,
        "timeout": 10,
    }
    
    session = SQLiteSession(session_id="student_session")
    triage_agent = create_triage_agent()
    
    # Use local MCP server for student data and content access
    async with MCPServerStreamableHttp(
        name="StudentDataToolbox",
        params=local_mcp_params,
        cache_tools_list=True,
        max_retry_attempts=3,
    ) as local_server:
        try:
            # Connect to MCP server
            await local_server.connect()
            # Add local MCP to triage agent
            triage_agent.mcp_servers = [local_server]
            
            result = await Runner.run(starting_agent=triage_agent, input="Hello", session=session)
            print(f"Olivia: {result.final_output}")

            while True:
                user_input = input("You: ")
                if user_input.lower() == "exit":
                    break
                result = await Runner.run(starting_agent=triage_agent, input=user_input, session=session)
                print(f"Olivia: {result.final_output}")
                
                if "handoff" in result.final_output.lower() or "tutor" in result.final_output.lower():
                    break
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":      
    asyncio.run(main())