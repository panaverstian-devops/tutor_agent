import asyncio
import os
import sys
import json
from dotenv import load_dotenv, find_dotenv
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, Runner, ModelSettings, SQLiteSession, set_tracing_disabled, set_tracing_export_api_key, trace
from agents.mcp import MCPServerStreamableHttp

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all agents
from triage_agent import Agent as TriageAgent
from tutor_agent import create_tutor_agent_with_tools
from feedback_agent import create_feedback_agent
from safety_agent import create_safety_agent, check_content_safety

# Load environment variables
_ = load_dotenv(find_dotenv())

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

# MCP Server Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_SERVER = f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"

# Local MCP Server Configuration for Student Data and Content
LOCAL_MCP_SERVER_URL = os.getenv("LOCAL_MCP_SERVER_URL", "http://localhost:8000/mcp")

class StudentContext:
    """Shared context that all agents can access and update."""
    def __init__(self):
        self.student_name = None
        self.subject = None
        self.grade_level = None
        self.learning_style = None
        self.language = None
        self.session_id = None
        self.current_topic = None
        self.progress = {}
        self.assessment_results = []

class MultiAgentOrchestrator:
    """Orchestrates the multi-agent tutoring system."""
    
    def __init__(self):
        self.session = SQLiteSession(session_id="student_session")
        self.student_context = StudentContext()
        self.current_agent = None
        
        # Create all agents
        self.triage_agent = self._create_triage_agent()
        self.tutor_agent = create_tutor_agent_with_tools()
        self.feedback_agent = create_feedback_agent()
        self.safety_agent = create_safety_agent()
        
        # Set up MCP servers
        self._setup_mcp_servers()
    
    def _create_triage_agent(self):
        """Create the Triage Agent"""
        from PROMPTS.triage_prompt import Triage_Agent_Prompt
        return Agent(
            name="Olivia",
            instructions=Triage_Agent_Prompt,
            model=model,
            model_settings=ModelSettings(temperature=0.7),
        )
    
    def _setup_mcp_servers(self):
        """Set up MCP servers for the tutor agent"""
        self.mcp_servers = []
        
        # Tavily MCP for web search
        if TAVILY_API_KEY:
            tavily_mcp_params = {
                "url": TAVILY_SERVER,
                "timeout": 10,
            }
            
            self.tavily_server = MCPServerStreamableHttp(
                name="TavilySearchToolbox",
                params=tavily_mcp_params,
                cache_tools_list=True,
                max_retry_attempts=3,
            )
            self.mcp_servers.append(self.tavily_server)
        
        # Local MCP for student data and content
        local_mcp_params = {
            "url": LOCAL_MCP_SERVER_URL,
            "timeout": 10,
        }
        
        self.local_server = MCPServerStreamableHttp(
            name="StudentDataToolbox",
            params=local_mcp_params,
            cache_tools_list=True,
            max_retry_attempts=3,
        )
        self.mcp_servers.append(self.local_server)
        
        # Add all MCP servers to tutor agent
        self.tutor_agent.mcp_servers = self.mcp_servers
    
    async def start_triage_phase(self):
        """Start with triage agent to assess student needs"""
        self.current_agent = self.triage_agent
        
        # Connect to local MCP server
        await self.local_server.connect()
        self.triage_agent.mcp_servers = [self.local_server]
        
        result = await Runner.run(starting_agent=self.triage_agent, input="Hello", session=self.session)
        safety_check = await check_content_safety(self.safety_agent, result.final_output, "Triage greeting")
        
        if safety_check["status"] == "safe":
            print(f"Olivia: {result.final_output}")
        else:
            print("Olivia: Hello! I'm here to help assess your learning needs. What's your name?")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                return False
            
            result = await Runner.run(starting_agent=self.triage_agent, input=user_input, session=self.session)
            safety_check = await check_content_safety(self.safety_agent, result.final_output, "Triage response")
            
            if safety_check["status"] == "safe":
                print(f"Olivia: {result.final_output}")
            else:
                print("Olivia: I apologize, but I need to provide a safer response. Could you rephrase your question?")
            
            if "handoff" in result.final_output.lower() or "tutor" in result.final_output.lower():
                return True
    
    async def start_tutoring_phase(self):
        """Start the main tutoring phase"""
        self.current_agent = self.tutor_agent
        
        # Connect to all MCP servers
        for server in self.mcp_servers:
            await server.connect()
        
        result = await Runner.run(starting_agent=self.tutor_agent, input="Hello! I'm ready to learn. Please search for current information about computer science and show me what tools you have available.", session=self.session)
        safety_check = await check_content_safety(self.safety_agent, result.final_output, "Tutor greeting")
        
        if safety_check["status"] == "safe":
            print(f"Tutor: {result.final_output}")
        else:
            print("Tutor: I apologize, but I need to provide a safer response. How can I help you learn today?")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                return False
            elif user_input.lower() == "feedback":
                await self.handoff_to_feedback()
                continue
            else:
                result = await Runner.run(starting_agent=self.tutor_agent, input=user_input, session=self.session)
                safety_check = await check_content_safety(self.safety_agent, result.final_output, "Tutor response")
                
                if safety_check["status"] == "safe":
                    print(f"Tutor: {result.final_output}")
                else:
                    print("Tutor: I apologize, but I need to provide a safer response. Could you rephrase your question?")
    
    async def handoff_to_feedback(self):
        """Handoff to Feedback Agent for progress review"""
        feedback_result = await Runner.run(starting_agent=self.feedback_agent, input="Please provide feedback on my learning progress.", session=self.session)
        feedback_safety = await check_content_safety(self.safety_agent, feedback_result.final_output, "Feedback session")
        
        if feedback_safety["status"] == "safe":
            print(f"Feedback Agent: {feedback_result.final_output}")
        else:
            print("Feedback blocked by safety agent")
    
    async def run(self):
        """Run the complete multi-agent system"""
        with trace("Complete AI Tutor Workflow"):
            try:
                # Start with triage phase
                if await self.start_triage_phase():
                    # Move to tutoring phase
                    await self.start_tutoring_phase()
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(f"Error: {e}")

async def main():
    """Main entry point"""
    orchestrator = MultiAgentOrchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())