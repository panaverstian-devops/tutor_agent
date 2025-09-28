import asyncio
import os
import sys
import json
from dotenv import load_dotenv
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, Runner, ModelSettings, SQLiteSession, set_tracing_disabled, RunResult, ToolCallOutputItem

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

# Import assessment prompt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PROMPTS.assessment_agent_prompt import Assessment_Agent_Prompt

async def extract_json_payload(run_result: RunResult) -> str:
    """Custom output extractor for Assessment Agent. Extracts JSON payload from the agent's output."""
    for item in reversed(run_result.new_items):
        if isinstance(item, ToolCallOutputItem) and item.output.strip().startswith("{"):
            try:
                # Attempt to parse and re-serialize to ensure valid JSON
                json_data = json.loads(item.output.strip())
                return json.dumps(json_data, indent=2)
            except json.JSONDecodeError:
                continue # Not valid JSON, continue searching
    # Fallback to a default JSON object if nothing was found or valid
    return json.dumps({
        "student_name": "Unknown",
        "assessment_date": "N/A",
        "subject": "N/A",
        "topic": "N/A",
        "overall_score": 0,
        "learning_growth": "N/A",
        "strengths": [],
        "growth_areas": [],
        "positive_observations": [],
        "recommendations": [],
        "next_steps": [],
        "confidence_level": "low",
        "notes": "Assessment could not be completed"
    })

def create_assessment_agent():
    """Create and return the Assessment Agent configured as a tool"""
    return Agent(
        name="AssessmentAgent",
        instructions=Assessment_Agent_Prompt,
        model=model,
        model_settings=ModelSettings(temperature=0.3),
    )

async def main():
    """Test the Assessment Agent independently"""
    session = SQLiteSession(session_id="test_assessment")
    assessment_agent = create_assessment_agent()
    
    test_input = """
    Please assess this student's work:
    
    Student: John
    Subject: Mathematics
    Topic: Algebra
    Student's Answer: "I solved the equation 2x + 5 = 13 by subtracting 5 from both sides to get 2x = 8, then dividing by 2 to get x = 4. I checked my work by substituting back: 2(4) + 5 = 8 + 5 = 13. ✓"
    
    Please provide a comprehensive assessment.
    """
    
    result = await Runner.run(starting_agent=assessment_agent, input=test_input, session=session)
    print(f"Assessment Result: {result.final_output}")
    
    json_output = extract_json_payload(result)
    print(f"Extracted JSON: {json_output}")

if __name__ == "__main__":
    asyncio.run(main())