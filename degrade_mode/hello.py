from dotenv import load_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, set_tracing_disabled
import os

# Load environment variables
load_dotenv()
set_tracing_disabled(True)

# Setup provider
provider = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# Setup model
model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash-exp",
    openai_client=provider
)

# Create Agent
Agent1 = Agent(
    name="Assistant",
    instructions="A helpful assistant that can answer questions and provide information.",
    model=model
)

# Interactive loop
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit", "bye"]:
        print("Assistant: Goodbye! 👋")
        break
    
    response = Runner.run_sync(
        starting_agent=Agent1,
        input=user_input
    )
    
    print("Assistant:", response.final_output)
