#!/usr/bin/env python3
"""
Chainlit Integration for AI Tutor System
Integrates the MultiAgentOrchestrator with Chainlit for web interface
"""

import chainlit as cl
import asyncio
import json
import os
import sys
from contextlib import aclosing
from agents import Runner
from openai.types.responses import ResponseTextDeltaEvent

# Add current directory to path for imports (since we're already in backend)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'companion_agents'))

from companion_agents.main_orchestrator import MultiAgentOrchestrator, hybrid_agent
from enhanced_learning_pack_generator import EnhancedLearningPackGenerator
from offline_learning_agent import OfflineLearningAgent
# Global orchestrator instance
orchestrator = None

async def get_orchestrator():
    """Get or create the orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        orchestrator = MultiAgentOrchestrator()
    return orchestrator

async def cleanup_mcp_servers(mcp_servers):
    """Cleanup MCP servers"""
    for server in mcp_servers:
        try:
            if hasattr(server, 'disconnect'):
                await server.disconnect()
        except Exception as e:
            print(f"⚠️ Error disconnecting MCP server: {e}")

@cl.on_chat_start
async def start():
    """Initialize the chat session"""
    print("🔍 Starting new Chainlit session")
    
    try:
        # Get orchestrator
        orch = await get_orchestrator()
        
        # Store in session
        cl.user_session.set("orchestrator", orch)
        cl.user_session.set("current_phase", "triage")  # Start with triage
        cl.user_session.set("history", [])
        cl.user_session.set("offline_mode", False)
        
        # Get network status
        speed_mbps, is_degrade = orch.hybrid_agent.bandwidth_monitor.get_network_status(force_check=True)
        
        # Display system status
        status_message = f"""
🎓 AI Tutor System with Hybrid OpenAI/Ollama Fallback + Degrade Mode + Learning Packs

🔄 Hybrid System Status: {'OpenAI Primary' if orch.hybrid_agent.use_openai else 'Ollama Local'}
🌐 Network Status: {'Good' if speed_mbps > 130 else 'Slow'} ({speed_mbps:.1f} Mbps)
📚 Learning Pack System: Ready for offline study

💡 Available Commands:
• 'generate pack for chap X of [subject]' - Create learning pack
• 'offline' - Start offline learning session
• 'feedback' - Get progress feedback
• 'exit' - End session

Ready to help you learn! What's your name?
        """.strip()
        
        await cl.Message(content=status_message).send()
        
        # Store initial history
        history = cl.user_session.get("history", [])
        history.append({"role": "assistant", "content": status_message})
        cl.user_session.set("history", history)
        
    except Exception as e:
        error_text = f"⚠️ System setup failed: {str(e)}"
        print(error_text)
        await cl.Message(content=error_text).send()

@cl.on_chat_end
async def end():
    """Cleanup when chat ends"""
    orch = cl.user_session.get("orchestrator")
    if orch:
        try:
            # Cleanup MCP servers
            for server in orch.mcp_servers:
                if hasattr(server, 'disconnect'):
                    await server.disconnect()
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
    
    print("🔌 Chat session ended and cleaned up")

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages"""
    orch = cl.user_session.get("orchestrator")
    current_phase = cl.user_session.get("current_phase", "triage")
    offline_mode = cl.user_session.get("offline_mode", False)
    
    if orch is None:
        await cl.Message(content="⚠️ System not initialized. Please restart the chat.").send()
        return
    
    user_input = message.content.strip()
    
    # Handle special commands
    if user_input.lower().startswith("generate pack") or user_input.lower().startswith("generate_pack"):
        await handle_generate_pack(orch, user_input)
        return
    
    elif user_input.lower() == "offline":
        await handle_offline_mode(orch)
        return
    
    elif user_input.lower() == "feedback":
        await handle_feedback(orch)
        return
    
    elif user_input.lower() == "exit":
        await cl.Message(content="👋 Thank you for using the AI Tutor System! Goodbye!").send()
        return
    
    # Handle offline learning commands
    if offline_mode:
        await handle_offline_command(orch, user_input)
        return
    
    # Handle regular chat based on current phase
    if current_phase == "triage":
        await handle_triage_phase(orch, user_input)
    elif current_phase == "tutoring":
        await handle_tutoring_phase(orch, user_input)
    else:
        await handle_tutoring_phase(orch, user_input)

async def handle_generate_pack(orch, user_input):
    """Handle learning pack generation"""
    msg = cl.Message(content="📚 Generating learning pack...")
    await msg.send()
    
    try:
        file_path = await orch.generate_learning_pack(user_input=user_input)
        
        if file_path:
            success_message = f"""
✅ Enhanced learning pack generated successfully!

📁 File: {file_path}
📚 Source: MCP Book Content
❓ Quiz Questions: 5

The learning pack is ready for offline study. Use 'offline' command to start studying!
            """.strip()
            
            await msg.update(content=success_message)
        else:
            await msg.update(content="❌ Failed to generate learning pack. Please try again.")
            
    except Exception as e:
        await msg.update(content=f"❌ Error generating learning pack: {e}")

async def handle_offline_mode(orch):
    """Handle offline mode activation"""
    offline_response = orch.start_offline_learning()
    
    if "❌" in offline_response:
        await cl.Message(content=offline_response).send()
        return
    
    # Set offline mode
    cl.user_session.set("offline_mode", True)
    
    # Send welcome message
    await cl.Message(content=offline_response).send()
    
    # Show available commands
    commands_message = """
💡 Offline Learning Commands:
• 'study' - Read the study material
• 'quiz' - Take the assessment quiz
• 'summary' - Get chapter summary
• 'progress' - Check your progress
• 'help' - Show available commands
• 'back' - Return to main tutor

Ready to start learning! Type 'study' to begin.
    """.strip()
    
    await cl.Message(content=commands_message).send()

async def handle_offline_command(orch, user_input):
    """Handle offline learning commands"""
    if user_input.lower() == "back":
        cl.user_session.set("offline_mode", False)
        await cl.Message(content="🔄 Returning to main tutor session...").send()
        return
    
    # Get offline response
    offline_response = orch.handle_offline_command(user_input)
    
    # Send response
    await cl.Message(content=offline_response).send()
    
    # Save progress if needed
    if orch.offline_agent and user_input.lower() in ["study", "quiz", "summary"]:
        orch.offline_agent.save_progress()

async def handle_feedback(orch):
    """Handle feedback request"""
    msg = cl.Message(content="🔄 Getting feedback...")
    await msg.send()
    
    try:
        response = await orch.get_hybrid_response(
            "Please provide feedback on my learning progress. Give me encouragement and suggestions for improvement.", 
            "Feedback Agent"
        )
        await msg.update(content=response)
    except Exception as e:
        await msg.update(content=f"❌ Error getting feedback: {e}")

async def handle_triage_phase(orch, user_input):
    """Handle triage phase conversation"""
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        # Use hybrid system for response
        response = await orch.get_hybrid_response(user_input, "Olivia")
        
        # Stream the response
        await stream_response(msg, response)
        
        # Check if should move to tutoring phase
        if "handoff" in response.lower() or "tutor" in response.lower():
            cl.user_session.set("current_phase", "tutoring")
            await cl.Message(content="🔄 Moving to tutoring phase...").send()
        
        # Update history
        history = cl.user_session.get("history", [])
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})
        cl.user_session.set("history", history)
        
    except Exception as e:
        await msg.update(content=f"❌ Error in triage phase: {e}")

async def handle_tutoring_phase(orch, user_input):
    """Handle tutoring phase conversation"""
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        # Use hybrid system for response
        response = await orch.get_hybrid_response(user_input, "Tutor")
        
        # Stream the response
        await stream_response(msg, response)
        
        # Update history
        history = cl.user_session.get("history", [])
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})
        cl.user_session.set("history", history)
        
    except Exception as e:
        await msg.update(content=f"❌ Error in tutoring phase: {e}")

async def stream_response(msg, response):
    """Stream response character by character"""
    if not response:
        await msg.update(content="(no response)")
        return
    
    # Simulate streaming by sending chunks
    chunk_size = 3
    for i in range(0, len(response), chunk_size):
        chunk = response[i:i + chunk_size]
        await msg.stream_token(chunk)
        await asyncio.sleep(0.02)  # Small delay for streaming effect
    
    await msg.update()

# Run the Chainlit app
if __name__ == "__main__":
    import chainlit as cl
    cl.run()
