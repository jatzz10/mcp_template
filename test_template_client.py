#!/usr/bin/env python3
"""
Test the template MCP client with your current setup
"""

import asyncio
import json
import sys
from pathlib import Path

# Add template to path
template_path = Path(__file__).parent
sys.path.insert(0, str(template_path))

from mcp_client.base import MCPClientBase


async def test_template_client():
    """Test the template MCP client"""
    
    print("🧪 Testing Template MCP Client")
    print("=" * 40)
    
    # Server URL (make sure your template server is running on port 8002)
    server_url = "http://127.0.0.1:8002/mcp"
    
    # Create client
    client = MCPClientBase(server_url)
    
    try:
        # Connect to server
        print("🔌 Connecting to template server...")
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to server")
            print("💡 Make sure the template server is running:")
            print("   python run_template_server.py")
            return False
        print("✅ Connected to template server")
        
        # Test health check
        print("\n🏥 Testing health check...")
        health = await client.health_check()
        print(f"Health: {health['status']}")
        
        # List tools
        print("\n🔧 Testing list tools...")
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # List resources
        print("\n📄 Testing list resources...")
        resources = await client.list_resources()
        print(f"Found {len(resources)} resources:")
        for resource in resources:
            print(f"  - {resource['uri']}: {resource['description']}")
        
        # Test query tool
        print("\n🔍 Testing query_mysql tool...")
        try:
            result = await client.call_tool("query_mysql", {
                "query": "SELECT 1 as test_column, 'Hello Template!' as message",
                "limit": 5
            })
            print("✅ Query executed successfully")
            data = json.loads(result["content"])
            print(f"Result: {data}")
        except Exception as e:
            print(f"❌ Query failed: {e}")
        
        # Test schema resource
        print("\n📋 Testing schema resource...")
        try:
            schema_resource = await client.read_resource("mysql://schema")
            print("✅ Schema resource retrieved")
            schema_data = json.loads(schema_resource["content"])
            print(f"Schema has {schema_data['metadata']['total_tables']} tables")
        except Exception as e:
            print(f"❌ Schema resource failed: {e}")
        
        # Test server info resource
        print("\nℹ️  Testing server info resource...")
        try:
            server_info = await client.read_resource("server://info")
            print("✅ Server info retrieved")
            info_data = json.loads(server_info["content"])
            print(f"Server: {info_data['name']}")
            print(f"Data sources: {info_data['data_sources']}")
        except Exception as e:
            print(f"❌ Server info failed: {e}")
        
        # Disconnect
        await client.disconnect()
        print("\n✅ Template client test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Template client test failed: {e}")
        return False


async def main():
    """Run the client test"""
    success = await test_template_client()
    
    if success:
        print("\n🎉 Template client test passed!")
        print("\n📋 Next steps:")
        print("1. Test the FastAPI client:")
        print("   python examples/fastapi_client.py")
        print("2. Test REST API endpoints:")
        print("   curl http://localhost:3000/health")
        print("   curl http://localhost:3000/tools")
    else:
        print("\n⚠️  Template client test failed!")
        print("Make sure the template server is running first.")


if __name__ == "__main__":
    asyncio.run(main())
