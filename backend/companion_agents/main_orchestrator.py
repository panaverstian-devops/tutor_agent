import asyncio
import os
import sys
import json
import time
import urllib.request
import signal
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, Runner, ModelSettings, SQLiteSession, set_tracing_disabled, set_tracing_export_api_key, trace
from agents.mcp import MCPServerStreamableHttp
from ollama import AsyncClient

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all agents
from triage_agent import create_triage_agent
from tutor_agent import create_tutor_agent_with_tools
from feedback_agent import create_feedback_agent
from safety_agent import create_safety_agent, check_content_safety

# Import learning pack system
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from learning_pack_generator import LearningPackGenerator
from enhanced_learning_pack_generator import EnhancedLearningPackGenerator
from offline_learning_agent import OfflineLearningAgent

# Load environment variables
_ = load_dotenv(find_dotenv())

# Set up tracing with API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    set_tracing_export_api_key(OPENAI_API_KEY)

# Enable tracing for workflow monitoring
set_tracing_disabled(False)

# MCP Server Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_SERVER = f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"

# Local MCP Server Configuration for Student Data and Content
LOCAL_MCP_SERVER_URL = os.getenv("LOCAL_MCP_SERVER_URL", "http://localhost:8000/mcp")

# Degrade Mode Configuration
DEGRADE_THRESHOLD_MBPS = float(os.getenv("DEGRADE_THRESHOLD_MBPS", "130.0"))  # Switch to degrade mode below this speed

class BandwidthMonitor:
    """Monitors network bandwidth and determines degrade mode status"""
    
    def __init__(self, threshold_mbps: float = DEGRADE_THRESHOLD_MBPS):
        self.threshold_mbps = threshold_mbps
        self.last_speed = 0.0
        self.last_check_time = 0
        self.check_interval = 30  # Check every 30 seconds
        
    def check_bandwidth(self, url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSZtdNNVK-gDIF-vyrnNSy5_SEKN4z0FiwGeQ&s",
                       file_size_bytes=5 * 1024 * 1024, timeout_seconds=10):
        """
        Measures download speed (Mbps) by attempting to read the URL.
        Returns measured Mbps as float; returns 0.0 on error (no connection).
        """
        try:
            start_time = time.time()
            with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
                _ = response.read()  # read entire test resource
            duration = time.time() - start_time
            if duration <= 0:
                return 0.0
            # Convert bytes -> bits and compute megabits per second
            speed_mbps = (file_size_bytes * 8) / (duration * 1_000_000)
            return speed_mbps
        except Exception as e:
            # Silently handle bandwidth check errors
            return 0.0
    
    def get_network_status(self, force_check=False):
        """Get current network status with optional caching"""
        current_time = time.time()
        
        # Use cached result if recent enough and not forcing check
        if not force_check and current_time - self.last_check_time < self.check_interval:
            return self.last_speed, self.is_degrade_mode()
        
        # Perform new bandwidth check
        self.last_speed = self.check_bandwidth()
        self.last_check_time = current_time
        
        return self.last_speed, self.is_degrade_mode()
    
    def is_degrade_mode(self):
        """Determine if we should use degrade mode based on current speed"""
        return self.last_speed < self.threshold_mbps and self.last_speed > 0
    
    def is_offline(self):
        """Check if completely offline"""
        return self.last_speed == 0.0

@dataclass
class AdaptiveModelSettings:
    """Dynamic model settings based on network conditions"""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    is_degrade_mode: bool = False
    
    @classmethod
    def create_for_network_condition(cls, speed_mbps: float, threshold_mbps: float = DEGRADE_THRESHOLD_MBPS):
        """Create settings based on network speed"""
        is_degrade = speed_mbps < threshold_mbps and speed_mbps > 0
        is_offline = speed_mbps == 0.0
        
        if is_offline:
            # Offline mode - use Ollama with conservative settings
            return cls(
                temperature=0.7,
                max_tokens=4096,
                top_p=1.0,
                is_degrade_mode=True
            )
        elif is_degrade:
            # Degrade mode - reduced quality but still functional
            return cls(
                temperature=0.2,
                max_tokens=150,
                top_p=0.3,
                is_degrade_mode=True
            )
        else:
            # Full quality mode
            return cls(
                temperature=0.7,
                max_tokens=4096,
                top_p=1.0,
                is_degrade_mode=False
            )

class OllamaAgent:
    """Handles local Ollama model interactions with streaming support"""
    def __init__(self, model_name: str, host: str = "http://127.0.0.1:11434"):
        self.model_name = model_name
        self.host = host
        self.client = AsyncClient(host=host)
        self.conversation_history = []

    async def chat(self, user_input: str, temperature: float = 0.7, max_tokens: int = 5000):
        """Chat with Ollama model using streaming with optimized settings"""
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Get response from Ollama with streaming and optimized settings
        full_response = ""
        try:
            # Await the chat method first, then iterate
            chat_stream = await self.client.chat(
                model=self.model_name,
                messages=self.conversation_history,
                stream=True,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "num_ctx": 2048,  # Reduce context window for faster processing
                    "num_batch": 512,  # Optimize batch size
                    "num_thread": 4,   # Use 4 threads for faster processing
                    "repeat_penalty": 1.1,  # Slight penalty to avoid repetition
                    "top_k": 40,       # Limit vocabulary for faster generation
                    "top_p": 0.9,      # Nucleus sampling for faster generation
                    "tfs_z": 1.0,      # Tail free sampling
                    "typical_p": 1.0,  # Typical sampling
                    "mirostat": 0,     # Disable mirostat for speed
                    "mirostat_eta": 0.1,
                    "mirostat_tau": 5.0,
                    "repeat_last_n": 64,  # Reduce repetition context
                    "penalize_newline": True,  # Penalize newlines for faster responses
                    "stop": ["\n\n", "Human:", "User:"]  # Stop tokens for faster completion
                }
            )
            
            async for chunk in chat_stream:
                if hasattr(chunk, 'message') and chunk.message and chunk.message.content:
                    print(chunk.message.content, end="", flush=True)
                    full_response += chunk.message.content
        except Exception as e:
            print(f"⚠️ Ollama streaming error: {e}")
            # Fallback to non-streaming with same optimized settings
            resp = await self.client.chat(
                model=self.model_name,
                messages=self.conversation_history,
                stream=False,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "num_ctx": 2048,
                    "num_batch": 512,
                    "num_thread": 4,
                    "repeat_penalty": 1.1,
                    "top_k": 40,
                    "top_p": 0.9,
                    "tfs_z": 1.0,
                    "typical_p": 1.0,
                    "mirostat": 0,
                    "mirostat_eta": 0.1,
                    "mirostat_tau": 5.0,
                    "repeat_last_n": 64,
                    "penalize_newline": True,
                    "stop": ["\n\n", "Human:", "User:"]
                }
            )
            full_response = resp.message.content
        
        print()  # New line after streaming
        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": full_response})
        
        return full_response

class HybridAgent:
    """Hybrid agent that uses OpenAI with Ollama fallback and bandwidth-aware degrade mode"""
    def __init__(self, ollama_model_name: str = "llama3.1", openai_api_key: str = None):
        self.ollama_agent = OllamaAgent(model_name=ollama_model_name)
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.use_openai = False
        self.openai_client = None
        self.openai_model = None
        self.conversation_history = []  # Shared memory between models
        self.bandwidth_monitor = BandwidthMonitor()  # Add bandwidth monitoring
        
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
        """Chat using hybrid system with bandwidth-aware degrade mode"""
        # Check network status on every command (force check)
        speed_mbps, is_degrade = self.bandwidth_monitor.get_network_status(force_check=True)
        
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Sync memory with Ollama agent
        self.ollama_agent.conversation_history = self.conversation_history.copy()
        
        # Try to reconnect to OpenAI if we're currently using Ollama and network is good
        if not self.use_openai and self.openai_api_key and not is_degrade and speed_mbps > 0:
            try:
                # Test OpenAI connection
                test_client = AsyncOpenAI(api_key=self.openai_api_key)
                await test_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                # If successful, switch back to OpenAI
                self.openai_client = test_client
                self.openai_model = OpenAIChatCompletionsModel(
                    model="gpt-3.5-turbo",
                    openai_client=self.openai_client
                )
                self.use_openai = True
            except Exception:
                # OpenAI still not available, continue with Ollama
                pass
        
        # Use OpenAI if available and network conditions allow
        if self.use_openai and self.openai_client and speed_mbps > 0:
            try:
                # Determine OpenAI settings based on network condition
                if is_degrade:
                    # Degraded network - use less tokens, concise output
                    temperature = 0.3
                    max_tokens = 150
                    top_p = 0.3
                else:
                    # Good network - full quality
                    temperature = 0.7
                    max_tokens = 4096
                    top_p = 1.0
                
                # Try OpenAI with appropriate settings and streaming
                full_response = ""
                stream = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.conversation_history,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
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
                # OpenAI API error, switching to Ollama
                self.use_openai = False
                # Fall through to Ollama
        
        # Use Ollama when offline or low network (no degrade mode for Ollama)
        
        response = await self.ollama_agent.chat(user_input, temperature=0.7, max_tokens=5000)
        # Sync memory back from Ollama
        self.conversation_history = self.ollama_agent.conversation_history.copy()
        return response

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

# Initialize Hybrid System after class definitions
hybrid_agent = HybridAgent(ollama_model_name="llama3.1")

# Create API provider for Gemini (backup)
Provider = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Set up the chat completion model (use hybrid system)
if hybrid_agent.use_openai:
    model = hybrid_agent.openai_model
else:
    # Use Gemini as fallback if OpenAI is not available
    model = OpenAIChatCompletionsModel(
        model="gemini-2.0-flash",
        openai_client=Provider,
    )

# Make model available globally
global_model = model

class MultiAgentOrchestrator:
    """Orchestrates the multi-agent tutoring system with hybrid OpenAI/Ollama fallback."""
    
    def __init__(self):
        self.session = SQLiteSession(session_id="student_session")
        self.student_context = StudentContext()
        self.current_agent = None
        self.hybrid_agent = hybrid_agent  # Use the global hybrid agent
        
        # Create all agents
        self.triage_agent = self._create_triage_agent()
        self.tutor_agent = create_tutor_agent_with_tools()
        self.feedback_agent = create_feedback_agent()
        self.safety_agent = create_safety_agent()
        
        # Disable MCP servers to avoid ID conflicts
        self.mcp_servers = []
        print("⚠️ MCP servers disabled to avoid ID conflicts")
        
        # Initialize learning pack system
        self.learning_pack_generator = EnhancedLearningPackGenerator()
        self.offline_agent = None
        self.current_chapter = 1
        self.current_subject = "Mathematics"
    
    def _create_triage_agent(self):
        """Create the Triage Agent with adaptive settings"""
        # Get current network status for adaptive settings (force check)
        speed_mbps, is_degrade = self.hybrid_agent.bandwidth_monitor.get_network_status(force_check=True)
        adaptive_settings = AdaptiveModelSettings.create_for_network_condition(speed_mbps)
        
        # Create triage agent using the imported function
        triage_agent = create_triage_agent()
        
        # Update the model to use the global model
        triage_agent.model = global_model
        
        # Apply adaptive settings
        triage_agent.model_settings = ModelSettings(
            temperature=adaptive_settings.temperature,
            max_tokens=adaptive_settings.max_tokens,
            top_p=adaptive_settings.top_p
        )
        
        return triage_agent
    
    def _setup_mcp_servers(self):
        """Set up MCP servers for the tutor agent"""
        self.mcp_servers = []
        
        # Tavily MCP for web search (optional)
        if TAVILY_API_KEY:
            try:
                tavily_mcp_params = {
                    "url": TAVILY_SERVER,
                    "timeout": 5,
                }
                
                self.tavily_server = MCPServerStreamableHttp(
                    name="TavilySearchToolbox",
                    params=tavily_mcp_params,
                    cache_tools_list=False,  # Disable caching to avoid ID conflicts
                    max_retry_attempts=1,
                )
                self.mcp_servers.append(self.tavily_server)
                print("✅ Tavily MCP server configured")
            except Exception as e:
                print(f"⚠️ Tavily MCP setup failed: {e}")
        
        # Local MCP for student data and content (optional)
        try:
            local_mcp_params = {
                "url": LOCAL_MCP_SERVER_URL,
                "timeout": 5,
            }
            
            self.local_server = MCPServerStreamableHttp(
                name="StudentDataToolbox",
                params=local_mcp_params,
                cache_tools_list=False,  # Disable caching to avoid ID conflicts
                max_retry_attempts=1,
            )
            self.mcp_servers.append(self.local_server)
            print("✅ Local MCP server configured")
        except Exception as e:
            print(f"⚠️ Local MCP setup failed: {e}")
        
        # Add all MCP servers to tutor agent (will be connected later)
        self.tutor_agent.mcp_servers = self.mcp_servers
    
    async def get_hybrid_response(self, user_input: str, agent_name: str = "Agent"):
        """Get response using hybrid system (OpenAI with Ollama fallback)"""
        try:
            # Use hybrid agent for response
            response = await self.hybrid_agent.chat(user_input)
            return response
        except Exception as e:
            print(f"⚠️ Hybrid system error: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again."
    
    async def generate_learning_pack(self, subject: str = None, chapter: int = None, user_input: str = None):
        """Generate enhanced learning pack for next day's study using MCP tools"""
        
        # Parse user input for subject and chapter if provided
        if user_input:
            user_input_lower = user_input.lower()
            if "english" in user_input_lower:
                subject = "English"
            elif "math" in user_input_lower or "mathematics" in user_input_lower:
                subject = "Mathematics"
            elif "science" in user_input_lower:
                subject = "Science"
            elif "history" in user_input_lower:
                subject = "History"
            
            # Extract chapter number
            import re
            chapter_match = re.search(r'chap(?:ter)?\s*(\d+)', user_input_lower)
            if chapter_match:
                chapter = int(chapter_match.group(1))
        
        if not subject:
            subject = self.current_subject
        if not chapter:
            chapter = self.current_chapter
        
        print(f"📚 Generating enhanced learning pack for {subject} - Chapter {chapter}")
        print("🔍 Using MCP tools to extract book content...")
        
        try:
            learning_pack = await self.learning_pack_generator.generate_enhanced_learning_pack(
                subject=subject,
                chapter_number=chapter,
                student_level="beginner"
            )
            
            # Save the learning pack
            file_path = self.learning_pack_generator.save_learning_pack(learning_pack)
            
            if file_path:
                print(f"✅ Enhanced learning pack generated successfully!")
                print(f"📁 File: {file_path}")
                print(f"📖 Subject: {subject}")
                print(f"📝 Chapter: {chapter}")
                print(f"📚 Source: {learning_pack['pack_info']['source']}")
                print(f"❓ Quiz Questions: {learning_pack['assessment']['total_questions']}")
                return file_path
            else:
                print("❌ Failed to save learning pack")
                return None
                
        except Exception as e:
            print(f"❌ Error generating learning pack: {e}")
            return None
    
    def start_offline_learning(self, learning_pack_path: str = None):
        """Start offline learning session"""
        if not learning_pack_path:
            # Use the main learning_pack.json file
            learning_pack_path = "/Users/mac/tutor_agent/backend/learning_pack.json"
        
        self.offline_agent = OfflineLearningAgent(learning_pack_path)
        
        if self.offline_agent.learning_pack:
            print("🔄 Starting offline learning session...")
            return self.offline_agent.start_study_session()
        else:
            return "❌ No learning pack found. Please generate one first using 'generate_pack' command."
    
    def handle_offline_command(self, user_input: str):
        """Handle commands for offline learning"""
        if not self.offline_agent:
            return "❌ No offline learning session active. Use 'offline' command to start."
        
        return self.offline_agent.handle_command(user_input)
    
    async def start_triage_phase(self):
        """Start with triage agent to assess student needs using hybrid system"""
        self.current_agent = self.triage_agent
        
        # Disable MCP servers for triage agent to avoid ID conflicts
        print("⚠️ MCP servers disabled for triage agent to avoid ID conflicts")
        self.triage_agent.mcp_servers = []
        
        # Use triage agent for proper greeting and assessment
        print("🔄 Starting triage phase with Olivia...")
        print("\nOlivia: ", end="", flush=True)
        
        # Use the actual triage agent instead of generic hybrid response
        try:
            # Use the triage agent with the existing session
            result = await Runner.run(
                self.triage_agent,
                "Hello! I'm a new student. Please help me get started with my learning assessment.",
                session=self.session
            )
            
            # Print the response
            print(result.final_output)
            print("\n")
            
        except Exception as e:
            print(f"⚠️ Triage agent error: {e}")
            # Fallback to hybrid system
            response = await self.get_hybrid_response("Hello! I'm Olivia, your AI teaching assistant. I'm here to help assess your learning needs and connect you with the perfect tutor. What's your name?", "Olivia")
            print("\n")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                return False
            elif user_input.lower().startswith("generate pack") or user_input.lower().startswith("generate_pack"):
                # Generate learning pack for next day
                print("📚 Generating learning pack for next day...")
                await self.generate_learning_pack(user_input=user_input)
                continue
            elif user_input.lower() == "offline":
                # Start offline learning session
                offline_response = self.start_offline_learning()
                print(f"\n{offline_response}\n")
                
                # Handle offline learning commands
                while True:
                    offline_input = input("Offline> ")
                    if offline_input.lower() == "back":
                        break
                    elif offline_input.lower() == "exit":
                        return False
                    else:
                        offline_response = self.handle_offline_command(offline_input)
                        print(f"\n{offline_response}\n")
                continue
            
            # Use triage agent for proper assessment
            print("Olivia: ", end="", flush=True)
            try:
                # Use the triage agent with existing session
                result = await Runner.run(
                    self.triage_agent,
                    user_input,
                    session=self.session
                )
                
                # Print the response
                print(result.final_output)
                print("\n")
                response = result.final_output
                
            except Exception as e:
                print(f"⚠️ Triage agent error: {e}")
                # Fallback to hybrid system
                response = await self.get_hybrid_response(user_input, "Olivia")
                print("\n")
            
            if "handoff" in response.lower() or "tutor" in response.lower():
                return True
    
    async def start_tutoring_phase(self):
        """Start the main tutoring phase using hybrid system"""
        self.current_agent = self.tutor_agent
        
        # Disable MCP servers for tutor agent to avoid ID conflicts
        print("⚠️ MCP servers disabled for tutor agent to avoid ID conflicts")
        self.tutor_agent.mcp_servers = []
        
        # Use tutor agent for proper teaching with curriculum content
        print("🔄 Starting tutoring phase with curriculum content...")
        print("\nTutor: ", end="", flush=True)
        
        # Use the tutor agent with curriculum content
        try:
            result = await Runner.run(
                self.tutor_agent,
                "Hello! I'm your AI tutor. I'm ready to help you learn with personalized teaching methods. I have access to the official Grade 7 curriculum, web search, and assessment tools. What would you like to learn about today?",
                session=self.session
            )
            
            # Print the response
            print(result.final_output)
            print("\n")
            
        except Exception as e:
            print(f"⚠️ Tutor agent error: {e}")
            # Fallback to hybrid system
            response = await self.get_hybrid_response("Hello! I'm your AI tutor. I'm ready to help you learn with personalized teaching methods. I have access to web search, PDF content, and assessment tools. What would you like to learn about today?", "Tutor")
            print("\n")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                return False
            elif user_input.lower() == "feedback":
                await self.handoff_to_feedback()
                continue
            elif user_input.lower().startswith("generate pack") or user_input.lower().startswith("generate_pack"):
                # Generate learning pack for next day
                print("📚 Generating learning pack for next day...")
                await self.generate_learning_pack(user_input=user_input)
                continue
            elif user_input.lower() == "offline":
                # Start offline learning session
                offline_response = self.start_offline_learning()
                print(f"\n{offline_response}\n")
                
                # Handle offline learning commands
                while True:
                    offline_input = input("Offline> ")
                    if offline_input.lower() == "back":
                        break
                    elif offline_input.lower() == "exit":
                        return False
                    else:
                        offline_response = self.handle_offline_command(offline_input)
                        print(f"\n{offline_response}\n")
                continue
            else:
                # Use tutor agent for proper teaching with book content
                print("Tutor: ", end="", flush=True)
                try:
                    # Use the tutor agent with existing session (MCP servers already disabled)
                    result = await Runner.run(
                        self.tutor_agent,
                        user_input,
                        session=self.session
                    )
                    
                    # Print the response
                    print(result.final_output)
                    print("\n")
                    response = result.final_output
                    
                except Exception as e:
                    print(f"⚠️ Tutor agent error: {e}")
                    # Fallback to hybrid system
                    response = await self.get_hybrid_response(user_input, "Tutor")
                    print("\n")
    
    async def handoff_to_feedback(self):
        """Handoff to Feedback Agent for progress review using hybrid system"""
        print("🔄 Using hybrid system for feedback...")
        print("\nFeedback Agent: ", end="", flush=True)
        try:
            # Use the feedback agent with existing session
            result = await Runner.run(
                self.feedback_agent,
                "Please provide feedback on my learning progress. Give me encouragement and suggestions for improvement.",
                session=self.session
            )
            
            # Print the response
            print(result.final_output)
            print("\n")
            response = result.final_output
            
        except Exception as e:
            print(f"⚠️ Feedback agent error: {e}")
            # Fallback to hybrid system
            response = await self.get_hybrid_response("Please provide feedback on my learning progress. Give me encouragement and suggestions for improvement.", "Feedback Agent")
            print("\n")
    
    async def run(self):
        """Run the complete multi-agent system"""
        with trace("Complete AI Tutor Workflow"):
            try:
                # Start with triage phase
                if await self.start_triage_phase():
                    # Move to tutoring phase
                    await self.start_tutoring_phase()
            except KeyboardInterrupt:
                print("\n👋 System stopped by user")
            except Exception as e:
                print(f"Error: {e}")
            finally:
                # Clean up MCP server connections
                try:
                    for server in self.mcp_servers:
                        try:
                            if hasattr(server, 'disconnect'):
                                await asyncio.wait_for(server.disconnect(), timeout=1.0)
                        except Exception:
                            pass  # Ignore individual server cleanup errors
                except Exception:
                    pass  # Ignore cleanup errors

async def main():
    """Main entry point with hybrid system, degrade mode, and learning packs"""
    print("🎓 AI Tutor System with Hybrid OpenAI/Ollama Fallback + Degrade Mode + Learning Packs")
    print("=" * 80)
    print(f"🔄 Hybrid System Status: {'OpenAI Primary' if hybrid_agent.use_openai else 'Ollama Local'}")
    
    # Check initial network status (force check)
    speed_mbps, is_degrade = hybrid_agent.bandwidth_monitor.get_network_status(force_check=True)
    if speed_mbps == 0.0:
        print(f"🌐 Network Status: Offline (0.0 Mbps) - Using Ollama")
    elif is_degrade:
        print(f"🌐 Network Status: Slow ({speed_mbps:.1f} Mbps) - OpenAI Degrade mode (150 tokens, temp=0.3)")
    else:
        print(f"🌐 Network Status: Good ({speed_mbps:.1f} Mbps) - OpenAI Full quality mode")
    
    print(f"⚙️ Degrade Threshold: {DEGRADE_THRESHOLD_MBPS} Mbps")
    print("📚 Learning Pack System: Ready for offline study")
    print("=" * 80)
    print("💡 New Commands Available:")
    print("   • 'generate_pack' - Create learning pack for next day")
    print("   • 'offline' - Start offline learning session")
    print("=" * 80)
    
    orchestrator = MultiAgentOrchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())