# 🎓 AI Tutor System - Clean Version

## 🚀 Quick Start

### Step 1: Start MCP Server
```bash
cd Mcp_Tools
python main.py
```

### Step 2: Run Complete System
```bash
cd tutor_agent/backend
python run_system.py
```

## 📁 Project Structure

```
tutor_agent/backend/
├── run_system.py              # Main entry point
├── Haka_Agents/
│   ├── main_orchestrator.py   # Complete system orchestrator
│   ├── triage_agent.py        # Triage agent (Olivia)
│   ├── tutor_agent.py         # Tutor agent with tools
│   ├── assessment_agent.py    # Assessment tool
│   ├── feedback_agent.py      # Feedback agent
│   └── safety_agent.py        # Safety monitoring
├── PROMPTS/
│   ├── triage_prompt.py       # Triage agent instructions
│   ├── tutor_agent_prompt.py  # Tutor agent instructions
│   ├── assessment_agent_prompt.py
│   ├── feedback_agent_prompt.py
│   └── safety_agent_prompt.py
└── README.md                  # This file
```

## 🔧 Environment Variables

Create a `.env` file with:
```env
# OpenAI API Key for tracing and general use
OPENAI_API_KEY=your_openai_api_key

# Gemini API Key for the main AI model
GEMINI_API_KEY=your_gemini_api_key

# Tavily API Key for web search
TAVILY_API_KEY=your_tavily_api_key

# Local MCP Server URL (usually localhost)
LOCAL_MCP_SERVER_URL=http://localhost:8000/mcp
```

## 🎮 Individual Agent Testing

```bash
# Test individual agents
cd tutor_agent/backend/Haka_Agents

# Triage Agent
python triage_agent.py

# Tutor Agent  
python tutor_agent.py

# Assessment Agent
python assessment_agent.py

# Feedback Agent
python feedback_agent.py

# Safety Agent
python safety_agent.py
```

## ✅ What's Clean

- ✅ Removed all unnecessary print statements
- ✅ Simplified code structure
- ✅ Clean error handling
- ✅ Minimal output - only essential messages
- ✅ Easy to run with simple commands

## 🎯 System Flow

1. **Triage Phase**: Olivia greets and assesses student
2. **Tutoring Phase**: Main tutor teaches with tools
3. **Feedback Phase**: Progress review and encouragement
4. **Safety**: Continuous content monitoring

## 🚨 Important

- Always start MCP server first
- Keep MCP server running during use
- System requires both API keys to function
