#!/usr/bin/env python3
"""
Test script to verify MCP server connection and tools.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from agents.mcp import MCPServerStreamableHttp

# Load environment variables
load_dotenv()

# Local MCP Server Configuration
LOCAL_MCP_SERVER_URL = os.getenv("LOCAL_MCP_SERVER_URL", "http://localhost:8000/mcp")

async def test_mcp_connection():
    """Test MCP server connection and available tools"""
    local_mcp_params = {
        "url": LOCAL_MCP_SERVER_URL,
        "timeout": 10,
    }
    
    print("🔍 Testing MCP Server Connection...")
    print(f"Server URL: {LOCAL_MCP_SERVER_URL}")
    print("=" * 50)
    
    try:
        async with MCPServerStreamableHttp(
            name="StudentDataToolbox",
            params=local_mcp_params,
            cache_tools_list=True,
            max_retry_attempts=3,
        ) as local_server:
            
            # Connect to server
            await local_server.connect()
            print("✅ Successfully connected to MCP server!")
            
            # List available tools
            tools = await local_server.list_tools()
            print(f"\n📋 Available Tools ({len(tools)}):")
            for i, tool in enumerate(tools, 1):
                print(f"  {i}. {tool.name}: {tool.description}")
            
            # Test a simple tool call
            print(f"\n🧪 Testing get_student_profile tool...")
            try:
                result = await local_server.call_tool("get_student_profile", {"user_id": "muhammad"})
                print(f"✅ Tool call successful: {result}")
            except Exception as e:
                print(f"❌ Tool call failed: {e}")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Make sure the MCP server is running:")
        print("   cd Mcp_Tools")
        print("   python main.py")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
