import asyncio
import os
import sys
from dotenv import load_dotenv
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, Runner, ModelSettings, SQLiteSession, set_tracing_disabled

# Load environment variables
load_dotenv()

# Disable extra tracing/logging for cleaner output
set_tracing_disabled(True)

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

# Import feedback prompt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PROMPTS.feedback_agent_prompt import Feedback_Agent_Prompt

def create_feedback_agent():
    """Create and return the Feedback Agent"""
    return Agent(
        name="FeedbackAgent",
        instructions=Feedback_Agent_Prompt,
        model=model,
        model_settings=ModelSettings(temperature=0.7),
    )

async def main():
    """Test the Feedback Agent independently"""
    session = SQLiteSession(session_id="test_feedback")
    feedback_agent = create_feedback_agent()
    
    test_input = """
    Please provide feedback to this student:
    
    Student: Sarah
    Subject: English Literature
    Recent Performance: 
    - Completed 3 chapters of "To Kill a Mockingbird"
    - Scored 85% on comprehension quiz
    - Participated actively in discussions
    - Struggled with essay writing structure
    
    Please provide caring feedback and ask about their learning experience.
    """
    
    result = await Runner.run(starting_agent=feedback_agent, input=test_input, session=session)
    print(f"Feedback: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())