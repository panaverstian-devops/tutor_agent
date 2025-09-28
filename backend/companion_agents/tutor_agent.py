import asyncio
import os
import sys
import json
from dotenv import load_dotenv, find_dotenv
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, Runner, ModelSettings, SQLiteSession, set_tracing_disabled, set_tracing_export_api_key, trace, RunResult, ToolCallOutputItem
from agents.mcp import MCPServerStreamableHttp

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import other agents
from assessment_agent import create_assessment_agent, extract_json_payload
from feedback_agent import create_feedback_agent
from safety_agent import create_safety_agent, check_content_safety

# Load environment variables from .env
_ = load_dotenv(find_dotenv())

# Set up tracing with API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    set_tracing_export_api_key(OPENAI_API_KEY)

# Enable tracing for workflow monitoring
set_tracing_disabled(False)

Provider = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Set up the chat completion model with the API provider
model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=Provider,
)

# MCP Server Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_SERVER = f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"

# Local MCP Server Configuration for Student Data and Content
LOCAL_MCP_SERVER_URL = os.getenv("LOCAL_MCP_SERVER_URL", "http://localhost:8000/mcp")

# Import tutor prompt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PROMPTS.tutor_agent_prompt import Tutor_Agent_Prompt

def create_tutor_agent_with_tools():
    """Create the Tutor Agent with Assessment Agent as a tool and Tavily MCP."""
    # Create Assessment Agent as a tool
    assessment_agent = create_assessment_agent()
    
    # Create Assessment Agent tool with custom JSON extraction
    assessment_tool = assessment_agent.as_tool(
        tool_name="conduct_assessment",
        tool_description="Conduct a formal assessment of student understanding and return detailed results in JSON format",
        custom_output_extractor=extract_json_payload,
    )
    
    # Create Tutor Agent with tools
    tutor_agent = Agent(
        name="TutorAgent",
        instructions=Tutor_Agent_Prompt,
        model=None,  # Will be set by orchestrator
        model_settings=ModelSettings(temperature=0.7),
        tools=[assessment_tool],
    )
    
    return tutor_agent

async def main():
    # Set up MCP server parameters
    tavily_mcp_params = {
        "url": TAVILY_SERVER,
        "timeout": 10,
    }
    
    local_mcp_params = {
        "url": LOCAL_MCP_SERVER_URL,
        "timeout": 20,
    }
    
    # Create agents
    tutor_agent = create_tutor_agent_with_tools()
    feedback_agent = create_feedback_agent()
    safety_agent = create_safety_agent()
    
    # Use both Tavily and Local MCP servers
    async with MCPServerStreamableHttp(
        name="TavilySearchToolbox",
        params=tavily_mcp_params,
        cache_tools_list=True,
        max_retry_attempts=3,
    ) as tavily_server, MCPServerStreamableHttp(
        name="StudentDataToolbox",
        params=local_mcp_params,
        cache_tools_list=True,
        max_retry_attempts=3,
    ) as local_server:
        try:
            session = SQLiteSession(session_id="student_session")

            # Connect to MCP servers
            await tavily_server.connect()
            await local_server.connect()
            
            # Add both MCP servers to tutor agent
            tutor_agent.mcp_servers = [tavily_server, local_server]

            # Get the first response from the agent
            result = await Runner.run(starting_agent=tutor_agent, input="Hello! I'm ready to learn.", session=session)
            
            # Check content safety before displaying
            safety_check = await check_content_safety(safety_agent, result.final_output, "Tutor greeting")
            
            if safety_check["status"] == "safe":
                print(f"Tutor: {result.final_output}")
            else:
                print("Tutor: I apologize, but I need to provide a safer response. How can I help you learn today?")

            # Interactive chat loop
            while True:
                user_input = input("You: ")
                if user_input.lower() == "exit":
                    break
                elif user_input.lower() == "feedback":
                    # Handoff to Feedback Agent
                    feedback_result = await Runner.run(starting_agent=feedback_agent, input="Please provide feedback on my learning progress.", session=session)
                    feedback_safety = await check_content_safety(safety_agent, feedback_result.final_output, "Feedback session")
                    
                    if feedback_safety["status"] == "safe":
                        print(f"Feedback Agent: {feedback_result.final_output}")
                    else:
                        print("Feedback blocked by safety agent")
                    continue
                else:  
                    result = await Runner.run(starting_agent=tutor_agent, input=user_input, session=session)
                    safety_check = await check_content_safety(safety_agent, result.final_output, "Tutor response")
                    
                    if safety_check["status"] == "safe":
                        print(f"Tutor: {result.final_output}")
                    else:
                        print("Tutor: I apologize, but I need to provide a safer response. Could you rephrase your question?")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())