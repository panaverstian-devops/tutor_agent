# Multi-Agent AI Tutor System

A comprehensive AI tutoring system with multiple specialized agents, handoffs, and tool integration using the OpenAI Agents SDK.

## 🏗️ Architecture

The system follows the agent architecture you specified:

1. **Triage Agent (Olivia)** - Warm, friendly greeting and VARK learning assessment
2. **Tutor Agent** - Main teaching agent with Assessment Agent as tool and Tavily MCP
3. **Assessment Agent** - Tool agent that provides structured JSON assessments
4. **Feedback Agent** - Caring principal-like agent for progress reviews
5. **Safety Agent** - Monitors all outputs for safety and policy compliance
6. **Shared Student Context** - All agents share and update student progress

## 📁 Project Structure

```
tutor_agent/backend/
├── PROMPTS/                    # All agent prompts in separate files
│   ├── triage_prompt.py       # Triage Agent prompt
│   ├── tutor_agent_prompt.py  # Tutor Agent prompt
│   ├── assessment_agent_prompt.py  # Assessment Agent prompt
│   ├── feedback_agent_prompt.py    # Feedback Agent prompt
│   └── safety_agent_prompt.py      # Safety Agent prompt
├── Haka_Agents/               # Agent implementation files
│   ├── triage_agent.py        # Triage Agent implementation
│   ├── tutor_agent.py         # Tutor Agent with tools
│   ├── assessment_agent.py    # Assessment Agent as tool
│   ├── feedback_agent.py      # Feedback Agent implementation
│   ├── safety_agent.py        # Safety Agent implementation
│   ├── main_orchestrator.py   # Main system orchestrator
│   └── README.md              # This file
```

## 🚀 Quick Start

### 1. Set Environment Variables

Create a `.env` file in the backend directory:

```env
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### 2. Run the Complete System

```bash
cd tutor_agent/backend/Haka_Agents
uv run main_orchestrator.py
```

### 3. Run Individual Agents (for testing)

```bash
# Test Triage Agent
uv run triage_agent.py

# Test Tutor Agent with tools
uv run tutor_agent.py

# Test Assessment Agent
uv run assessment_agent.py

# Test Feedback Agent
uv run feedback_agent.py

# Test Safety Agent
uv run safety_agent.py
```

## 🔄 Agent Flow

### 1. Triage Phase
- Student starts with Olivia (Triage Agent)
- Collects student information (name, subject, grade, learning style)
- Hands off to Tutor Agent when assessment is complete

### 2. Tutoring Phase
- Tutor Agent with Tavily search capabilities
- Assessment Agent as tool for understanding checks
- Safety monitoring for all responses
- Option to handoff to Feedback Agent

### 3. Feedback Phase
- Feedback Agent provides caring, principal-like feedback
- Reviews student progress and learning experience
- Returns to Tutor Agent for continued learning

## 🛠️ Key Features

### Assessment Agent as Tool
```python
# Assessment Agent with custom JSON extraction
assessment_tool = assessment_agent.as_tool(
    tool_name="conduct_assessment",
    tool_description="Conduct a formal assessment of student understanding",
    custom_output_extractor=extract_json_payload,
)
```

### Custom JSON Output Extraction
```python
async def extract_json_payload(run_result: RunResult) -> str:
    # Extracts structured JSON from Assessment Agent output
    for item in reversed(run_result.new_items):
        if isinstance(item, ToolCallOutputItem) and item.output.strip().startswith("{"):
            return item.output.strip()
    return "{}"
```

### Shared Student Context
```python
class StudentContext:
    def __init__(self):
        self.student_name = None
        self.subject = None
        self.learning_style = None
        self.progress_percent = 0
        self.assessments = []
        self.feedback_history = []
```

### Safety Monitoring
```python
# All agent outputs are checked for safety
safety_check = await check_content_safety(safety_agent, content, context)
if safety_check["status"] == "safe":
    # Display content
elif safety_check["status"] == "blocked":
    # Block and provide alternative
```

## 🎯 Usage Examples

### Complete System Flow
1. Run `main_orchestrator.py`
2. Start with Triage Agent (Olivia)
3. Provide student information
4. Get handed off to Tutor Agent
5. Learn with assessment tools and Tavily search
6. Request feedback when needed
7. Continue learning cycle

### Individual Agent Testing
- Each agent can be run independently for testing
- All agents share the same session context
- Safety monitoring works across all agents

## 🔧 Configuration

### MCP Integration
- Tavily MCP for web search capabilities
- Configurable MCP server URLs and tokens
- Automatic retry and caching for reliability

### Agent Settings
- Temperature settings optimized for each agent type
- Tool choice requirements for proper tool usage
- Custom output extractors for structured data

## 📊 Output Formats

### Assessment Agent JSON Output
```json
{
  "student_name": "John",
  "overall_score": 85,
  "strengths": ["Problem solving", "Conceptual understanding"],
  "weaknesses": ["Calculation errors", "Time management"],
  "good_points": ["Clear explanations", "Logical reasoning"],
  "areas_for_improvement": ["Double-checking work", "Practice more problems"],
  "recommendations": ["Review basic arithmetic", "Practice timed exercises"],
  "next_steps": ["Complete practice set", "Review error patterns"]
}
```

### Safety Agent Responses
- `SAFE`: Content is appropriate
- `WARNING`: Minor issues, can be used with modifications
- `BLOCK`: Content violates guidelines and must be blocked

## 🛡️ Safety Features

- All agent outputs monitored by Safety Agent
- Content filtering for educational appropriateness
- Policy compliance checking
- Automatic content blocking when necessary

## 🔄 Handoff System

- Triage → Tutor Agent (automatic after assessment)
- Tutor Agent → Feedback Agent (on request)
- Feedback Agent → Tutor Agent (automatic return)
- All handoffs maintain session context

This system provides a complete, safe, and effective AI tutoring experience with proper agent coordination and tool integration!
