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

# Import safety prompt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PROMPTS.safety_agent_prompt import Safety_Agent_Prompt

def create_safety_agent():
    """Create and return the Safety Agent"""
    return Agent(
        name="SafetyAgent",
        instructions=Safety_Agent_Prompt,
        model=model,
        model_settings=ModelSettings(temperature=0),
    )

async def check_content_safety(safety_agent, content_to_check, context=""):
    """Check if content is safe and appropriate"""
    session = SQLiteSession(session_id="safety_check")
    
    check_input = f"""
    Please review this agent output for safety and educational appropriateness:
    
    Context: {context}
    
    Content to Review:
    {content_to_check}
    
    Please provide your safety assessment.
    """
    
    result = await Runner.run(starting_agent=safety_agent, input=check_input, session=session)
    response = result.final_output.upper()
    
    if "SAFE" in response:
        return {"status": "safe", "message": result.final_output}
    elif "WARNING" in response:
        return {"status": "warning", "message": result.final_output}
    elif "BLOCK" in response:
        return {"status": "blocked", "message": result.final_output}
    else:
        return {"status": "unknown", "message": result.final_output}

async def main():
    """Test the Safety Agent independently"""
    session = SQLiteSession(session_id="test_safety")
    safety_agent = create_safety_agent()
    
    safe_content = """
    "Great job on solving that algebra problem! You correctly used the distributive property. 
    Let's practice a few more similar problems to reinforce this concept."
    """
    
    result = await check_content_safety(safety_agent, safe_content, "Math tutoring session")
    print(f"Safe Content Check: {result}")
    
    problematic_content = """
    "You're terrible at math and will never understand this. Give up now."
    """
    
    result = await check_content_safety(safety_agent, problematic_content, "Math tutoring session")
    print(f"Problematic Content Check: {result}")

if __name__ == "__main__":
    asyncio.run(main())