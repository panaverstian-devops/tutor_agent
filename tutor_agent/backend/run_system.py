#!/usr/bin/env python3
"""
Simple script to run the complete multi-agent tutoring system.
This is the main entry point for the entire system.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the Haka_Agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Haka_Agents'))

from main_orchestrator import main

if __name__ == "__main__":
    print("🎓 AI Tutor System Starting...")
    print("Make sure MCP server is running: python Mcp_Tools/main.py")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 System stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your environment variables are set correctly.")
