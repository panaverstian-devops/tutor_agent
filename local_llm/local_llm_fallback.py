import asyncio
import os
from agents import Agent, Runner, ModelSettings, SQLiteSession, AsyncOpenAI, OpenAIChatCompletionsModel
from ollama import AsyncClient
from dotenv import load_dotenv

load_dotenv()

class OllamaAgent:
    def __init__(self, model_name: str, host: str = "http://127.0.0.1:11434"):
        self.model_name = model_name
        self.host = host
        self.client = AsyncClient(host=host)
        self.conversation_history = []

    async def chat(self, user_input: str):
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Get response from Ollama with streaming
        full_response = ""
        try:
            # Await the chat method first, then iterate
            chat_stream = await self.client.chat(
                model=self.model_name,
                messages=self.conversation_history,
                stream=True
            )
            
            async for chunk in chat_stream:
                if hasattr(chunk, 'message') and chunk.message and chunk.message.content:
                    print(chunk.message.content, end="", flush=True)
                    full_response += chunk.message.content
        except Exception as e:
            print(f"⚠️ Ollama streaming error: {e}")
            # Fallback to non-streaming
            resp = await self.client.chat(
                model=self.model_name,
                messages=self.conversation_history,
                stream=False
            )
            full_response = resp.message.content
            print(full_response)
        
        print()  # New line after streaming
        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": full_response})
        
        return full_response

class HybridAgent:
    def __init__(self, ollama_model_name: str = "llama3.1", openai_api_key: str = None):
        self.ollama_agent = OllamaAgent(model_name=ollama_model_name)
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.use_openai = False
        self.openai_client = None
        self.openai_model = None
        self.conversation_history = []
        
        # Initialize OpenAI if API key is available
        if self.openai_api_key:
            try:
                self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
                self.openai_model = OpenAIChatCompletionsModel(
                    model="gpt-3.5-turbo",
                    openai_client=self.openai_client
                )
                self.use_openai = True
                print("✅ OpenAI API connected - using OpenAI for responses")
            except Exception as e:
                print(f"⚠️ OpenAI API connection failed: {e}")
                print("🔄 Falling back to Ollama local model")
                self.use_openai = False

    async def chat(self, user_input: str):
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        if self.use_openai and self.openai_client:
            try:
                # Try OpenAI first with streaming
                full_response = ""
                stream = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.conversation_history,
                    temperature=0.7,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        print(chunk.choices[0].delta.content, end="", flush=True)
                        full_response += chunk.choices[0].delta.content
                
                print()  # New line after streaming
                self.conversation_history.append({"role": "assistant", "content": full_response})
                return full_response
                
            except Exception as e:
                print(f"⚠️ OpenAI API error: {e}")
                print("🔄 Switching to Ollama local model")
                self.use_openai = False
                # Fall through to Ollama
        
        # Use Ollama as fallback or primary
        return await self.ollama_agent.chat(user_input)

async def main():
    # Create hybrid agent (OpenAI + Ollama fallback)
    hybrid_agent = HybridAgent(ollama_model_name="llama3.1")
    
    # Create session for conversation tracking
    session = SQLiteSession(session_id="student_session")
    
    # Create a simple agent that uses our hybrid agent
    TutorAgent = Agent(
        name="TutorAgent",
        model="gpt-3.5-turbo" if hybrid_agent.use_openai else "llama3.1",
        model_settings=ModelSettings(temperature=0.7),
        instructions="You are a helpful assistant. Always respond with exactly what the user asks for.",
    )

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break
        
        # Get response from hybrid agent (OpenAI with Ollama fallback)
        response = await hybrid_agent.chat(user_input)
        print(f"TutorAgent: {response}")

if __name__ == "__main__":
    asyncio.run(main())
