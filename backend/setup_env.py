#!/usr/bin/env python3
"""
Setup script to help users configure environment variables.
"""

import os
from pathlib import Path

def create_env_file():
    """Create a .env file with template values"""
    env_content = """# AI Tutor System Environment Variables
# Fill in your actual API keys below

# OpenAI API Key for tracing and general use
OPENAI_API_KEY=your_openai_api_key_here

# Gemini API Key for the main AI model
GEMINI_API_KEY=your_gemini_api_key_here

# Tavily API Key for web search
TAVILY_API_KEY=your_tavily_api_key_here

# Local MCP Server URL (usually localhost)
LOCAL_MCP_SERVER_URL=http://localhost:8000/mcp
"""
    
    env_file = Path(".env")
    if env_file.exists():
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("❌ Setup cancelled.")
            return False
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created successfully!")
    print("📝 Please edit .env file and add your actual API keys.")
    return True

def check_env_vars():
    """Check if all required environment variables are set"""
    required_vars = [
        "OPENAI_API_KEY",
        "GEMINI_API_KEY", 
        "TAVILY_API_KEY",
        "LOCAL_MCP_SERVER_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}_here":
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing or incomplete environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    else:
        print("✅ All environment variables are properly set!")
        return True

def main():
    print("🔧 AI Tutor System Environment Setup")
    print("=" * 40)
    
    # Check if .env exists
    if not Path(".env").exists():
        print("📝 Creating .env file...")
        create_env_file()
    else:
        print("📝 .env file found. Checking configuration...")
        if check_env_vars():
            print("🎉 Setup complete! You can now run the system.")
        else:
            print("📝 Please update your .env file with the correct API keys.")

if __name__ == "__main__":
    main()
