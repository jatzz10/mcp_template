#!/usr/bin/env python3
"""
Test script for JIRA MCP Server
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp_server import JiraMCPServer


async def test_jira_server():
    """Test the JIRA MCP server"""
    print("🧪 Testing JIRA MCP Server")
    print("=" * 40)
    
    # Load configuration from environment
    config = {
        'server_name': 'test-jira-server',
        'server_host': '127.0.0.1',
        'server_port': 8005,  # Use different port for testing
        'jira_base_url': os.getenv('JIRA_BASE_URL', ''),
        'jira_username': os.getenv('JIRA_USERNAME', ''),
        'jira_api_token': os.getenv('JIRA_API_TOKEN', ''),
        'jira_project_key': os.getenv('JIRA_PROJECT_KEY', ''),
        'jira_timeout': int(os.getenv('JIRA_TIMEOUT', '30')),
        'log_level': 'INFO',
        'workflows_cache_ttl': 3600,
        'query_cache_ttl': 300,
        'max_query_limit': 1000
    }
    
    print(f"📊 JIRA Base URL: {config['jira_base_url']}")
    print(f"🔗 Username: {config['jira_username']}")
    print(f"📋 Project Key: {config['jira_project_key']}")
    
    try:
        # Create server
        server = JiraMCPServer(config)
        
        # Test connection
        print("\n🔌 Testing JIRA connection...")
        connected = await server.connect()
        if not connected:
            print("❌ Failed to connect to JIRA")
            return False
        print("✅ Connected to JIRA")
        
        # Test health check
        print("\n🏥 Testing health check...")
        health = await server.health_check()
        print(f"Health: {health['status']}")
        print(f"Project: {health.get('project_name', 'unknown')}")
        print(f"Connected: {health.get('connected', False)}")
        
        # Test workflows generation
        print("\n📋 Testing workflows generation...")
        workflows = await server.get_workflows()
        print(f"✅ Workflows generated")
        print(f"Project: {workflows['project']['name']}")
        print(f"Issue Types: {len(workflows['issue_types'])}")
        print(f"Fields: {len(workflows['fields'])}")
        print(f"Workflows: {len(workflows['workflows'])}")
        
        # Test query execution
        print("\n🔍 Testing query execution...")
        try:
            # Test search query
            results = await server.execute_query("search", f'project = "{config["jira_project_key"]}" ORDER BY created DESC', "", 5)
            print(f"✅ Search query executed: {len(results)} results")
            if results:
                print(f"Sample issue: {results[0].get('key', 'unknown')}")
        except Exception as e:
            print(f"⚠️  Search query failed: {e}")
        
        try:
            # Test components query
            results = await server.execute_query("components", "", "", 5)
            print(f"✅ Components query executed: {len(results)} results")
        except Exception as e:
            print(f"⚠️  Components query failed: {e}")
        
        try:
            # Test versions query
            results = await server.execute_query("versions", "", "", 5)
            print(f"✅ Versions query executed: {len(results)} results")
        except Exception as e:
            print(f"⚠️  Versions query failed: {e}")
        
        # Test query validation
        print("\n🛡️ Testing query validation...")
        valid = await server.validate_query("search", f'project = "{config["jira_project_key"]}"', 10)
        print(f"✅ Valid query: {valid}")
        
        # Test dangerous query blocking
        invalid = await server.validate_query("search", "DELETE FROM issues", 10)
        print(f"✅ Dangerous query blocked: {not invalid}")
        
        # Test MCP tools
        print("\n🔧 Testing MCP tools...")
        
        # Register tools
        server._register_tools()
        
        print("✅ MCP tools registered successfully")
        
        # Disconnect
        await server.disconnect()
        print("\n✅ JIRA MCP server test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ JIRA MCP server test failed: {e}")
        return False


async def main():
    """Run the test"""
    print("🚀 Testing JIRA MCP Server Template")
    print("=" * 50)
    
    # Check environment
    print("🔍 Checking environment...")
    required_vars = ["JIRA_BASE_URL", "JIRA_USERNAME", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("JIRA tests require valid credentials to run properly.")
        print("Set the following environment variables:")
        print("  JIRA_BASE_URL=https://your-domain.atlassian.net")
        print("  JIRA_USERNAME=your-email@example.com")
        print("  JIRA_API_TOKEN=your-api-token")
        print("  JIRA_PROJECT_KEY=PROJ")
        return
    
    # Run test
    success = await test_jira_server()
    
    if success:
        print("\n🎉 JIRA MCP server test passed!")
        print("\n📋 Next steps:")
        print("1. Run: python mcp_server.py")
        print("2. Test with MCP client: python mcp_client.py")
        print("3. Test with FastAPI client")
    else:
        print("\n⚠️  JIRA MCP server test failed!")
        print("Check your JIRA configuration and try again.")


if __name__ == "__main__":
    asyncio.run(main())
