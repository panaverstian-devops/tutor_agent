# 🎓 Multi-Agent AI Tutor System with MCP Integration

## 🚀 Quick Start Guide

### 1. Start the MCP Server (Required First)
```bash
cd tutor_agent/backend
uv run start_mcp_server.py
```
**Keep this running in a separate terminal!**

### 2. Run the Complete System
```bash
cd tutor_agent/backend/Haka_Agents
uv run main_orchestrator.py
```

## 🔧 MCP Integration Overview

### Available MCP Tools

#### **Student Data & Content Tools (Local MCP)**
- `get_student_profile` - Get student information and learning preferences
- `get_course_basic_info` - Access course curriculum and structure  
- `get_table_of_contents` - Get organized course modules and topics
- `get_current_topic` - Access student's current learning position
- `pdf_reader_computer7` - Read Computer Science Grade 7 content
- `pdf_reader_english7` - Read English Grade 7 content

#### **Web Search Tools (Tavily MCP)**
- Real-time web search for current examples
- Educational resources and tutorials
- News and trends related to topics

### Agent MCP Usage

#### **Triage Agent (Olivia)**
- **MCP Server**: Local MCP only
- **Tools Used**: Student data tools for personalization
- **Purpose**: Access student profiles and course information during assessment

#### **Tutor Agent**
- **MCP Servers**: Both Tavily + Local MCP
- **Tools Used**: All available tools
- **Purpose**: 
  - Tavily: Find current examples and real-world applications
  - Local: Access curriculum content and student progress

## 📚 Student Mock Data

The system includes mock student data:

### Available Students
- **Muhammad Mustafa** (beginner, visual learner, CS-7)
- **Fatima Noor** (intermediate, auditory learner, EN-7)  
- **Ali Khan** (advanced, kinesthetic learner, CS-7)

### Available Courses
- **CS-7**: Computer Science Grade 7 (SNC 2023-24)
- **EN-7**: English Grade 7 (SNC 2023-24)

### Course Structure
Each course includes:
- 6 main units with descriptions
- Structured topic progression
- PDF content access for official curriculum

## 🎯 New Features Added

### Topic Sequence & Checkpoint System
- **Sequence Enforcement**: Students must follow the structured learning path
- **Skip Requests**: Handled with gentle persuasion and checkpoint quizzes
- **Checkpoint Quizzes**: 10-15 questions, 70% passing score required
- **Educational Reasoning**: Focus on mastery and foundation building

### Enhanced Agent Capabilities
- **Triage Agent**: Can access student data for personalized greetings
- **Tutor Agent**: Dual MCP access for comprehensive teaching
- **Content Integration**: Direct access to official curriculum PDFs
- **Progress Tracking**: Real-time student position and progress monitoring

## 🔄 Complete System Flow

1. **Triage Phase** (Olivia)
   - Warm greeting with student data access
   - VARK learning style assessment
   - Information collection and course selection
   - Handoff to Tutor Agent

2. **Tutoring Phase** (Tutor Agent)
   - Access to both web search and curriculum content
   - Structured lesson delivery with real-world examples
   - Assessment integration for progress tracking
   - Topic sequence enforcement with checkpoint system

3. **Feedback Phase** (Feedback Agent)
   - Progress review and encouragement
   - Learning experience feedback
   - Return to tutoring with insights

4. **Safety Monitoring** (Safety Agent)
   - Continuous content safety checks
   - Cultural sensitivity monitoring
   - Educational appropriateness validation

## 🛠️ Environment Setup

### Required Environment Variables
```env
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
LOCAL_MCP_SERVER_URL=http://localhost:8000/mcp
```

### File Structure
```
tutor_agent/backend/
├── Haka_Agents/
│   ├── main_orchestrator.py      # Complete system
│   ├── triage_agent.py           # Triage with local MCP
│   ├── tutor_agent.py            # Tutor with dual MCP
│   ├── assessment_agent.py       # Assessment tool
│   ├── feedback_agent.py         # Feedback agent
│   └── safety_agent.py           # Safety monitoring
├── PROMPTS/
│   ├── triage_prompt.py          # Updated with MCP tools
│   ├── tutor_agent_prompt.py     # Updated with sequence rules
│   ├── assessment_agent_prompt.py
│   ├── feedback_agent_prompt.py
│   └── safety_agent_prompt.py
├── start_mcp_server.py           # MCP server starter
└── MCP_INTEGRATION_README.md     # This file
```

## 🎮 Testing the System

### Individual Agent Testing
```bash
# Test Triage Agent with MCP
cd tutor_agent/backend/Haka_Agents
uv run triage_agent.py

# Test Tutor Agent with dual MCP
uv run tutor_agent.py

# Test other agents
uv run assessment_agent.py
uv run feedback_agent.py
uv run safety_agent.py
```

### Complete System Testing
```bash
# Terminal 1: Start MCP Server
cd tutor_agent/backend
uv run start_mcp_server.py

# Terminal 2: Start Complete System
cd tutor_agent/backend/Haka_Agents
uv run main_orchestrator.py
```

## 🔍 Key Improvements Made

1. **MCP Integration**: Both agents now have access to powerful tools
2. **Student Data Access**: Personalized experience based on mock data
3. **Curriculum Integration**: Direct access to official PDF content
4. **Topic Sequence Rules**: Structured learning with checkpoint system
5. **Enhanced Prompts**: Updated instructions for MCP tool usage
6. **Dual MCP Support**: Tutor agent uses both web search and local content

## 🚨 Important Notes

- **Always start the MCP server first** before running any agents
- **Keep MCP server running** in a separate terminal during testing
- **Mock data is available** for testing student interactions
- **PDF content access** requires the MCP server to be running
- **Topic sequence enforcement** ensures proper learning progression

## 🎉 Ready to Use!

Your multi-agent AI tutor system is now fully integrated with MCP tools and ready for comprehensive testing. The system provides:

- ✅ Personalized student assessment and greeting
- ✅ Curriculum-aligned content delivery
- ✅ Real-time web search for current examples
- ✅ Structured learning progression with checkpoints
- ✅ Comprehensive safety monitoring
- ✅ Caring feedback and progress tracking

Start with the MCP server, then run the main orchestrator for the complete experience! 🚀
