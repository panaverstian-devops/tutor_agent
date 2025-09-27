#!/usr/bin/env python3
"""
Test script to verify Tavily MCP integration and tools.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from agents.mcp import MCPServerStreamableHttp

# Load environment variables
load_dotenv()

# Tavily MCP Server Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_SERVER = f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"

async def test_tavily_mcp():
    """Test Tavily MCP server connection and available tools"""
    if not TAVILY_API_KEY:
        print("❌ TAVILY_API_KEY not found in environment variables")
        return
    
    tavily_mcp_params = {
        "url": TAVILY_SERVER,
        "timeout": 20,
    }
    
    print("🔍 Testing Tavily MCP Server Connection...")
    print(f"Server URL: {TAVILY_SERVER}")
    print("=" * 50)
    
    try:
        async with MCPServerStreamableHttp(
            name="TavilySearchToolbox",
            params=tavily_mcp_params,
            cache_tools_list=True,
            max_retry_attempts=3,
        ) as tavily_server:
            
            # Connect to server
            await tavily_server.connect()
            print("✅ Successfully connected to Tavily MCP server!")
            
            # List available tools
            tools = await tavily_server.list_tools()
            print(f"\n📋 Available Tavily Tools ({len(tools)}):")
            for i, tool in enumerate(tools, 1):
                print(f"  {i}. {tool.name}: {tool.description}")
            
            # Test a simple search
            print(f"\n🧪 Testing Tavily search...")
            try:
                result = await tavily_server.call_tool("tavily_search", {
                    "query": "artificial intelligence in education",
                    "max_results": 3
                })
                print(f"✅ Search successful!")
                print(f"Results: {result}")
            except Exception as e:
                print(f"❌ Search failed: {e}")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Make sure your Tavily API key is set correctly:")
        print("   TAVILY_API_KEY=your_tavily_api_key")

if __name__ == "__main__":
    asyncio.run(test_tavily_mcp())
