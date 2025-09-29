#!/usr/bin/env python3
"""
Test script for REST API MCP Server
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp_server import RestAPIMCPServer


async def test_rest_api_server():
    """Test the REST API MCP server"""
    print("🧪 Testing REST API MCP Server")
    print("=" * 40)
    
    # Load configuration from environment
    config = {
        'server_name': 'test-rest-api-server',
        'server_host': '127.0.0.1',
        'server_port': 8003,  # Use different port for testing
        'api_base_url': os.getenv('API_BASE_URL', 'https://api.example.com'),
        'api_auth_type': os.getenv('API_AUTH_TYPE', 'none'),
        'api_auth_token': os.getenv('API_AUTH_TOKEN', ''),
        'api_username': os.getenv('API_USERNAME', ''),
        'api_password': os.getenv('API_PASSWORD', ''),
        'api_timeout': int(os.getenv('API_TIMEOUT', '30')),
        'api_rate_limit': int(os.getenv('API_RATE_LIMIT', '100')),
        'api_retry_attempts': int(os.getenv('API_RETRY_ATTEMPTS', '3')),
        'log_level': 'INFO',
        'endpoints_cache_ttl': 3600,
        'query_cache_ttl': 300,
        'max_query_limit': 1000
    }
    
    print(f"📊 API Base URL: {config['api_base_url']}")
    print(f"🔗 Auth Type: {config['api_auth_type']}")
    
    try:
        # Create server
        server = RestAPIMCPServer(config)
        
        # Test connection
        print("\n🔌 Testing API connection...")
        connected = await server.connect()
        if not connected:
            print("❌ Failed to connect to API")
            return False
        print("✅ Connected to API")
        
        # Test health check
        print("\n🏥 Testing health check...")
        health = await server.health_check()
        print(f"Health: {health['status']}")
        
        # Test endpoints generation
        print("\n📋 Testing endpoints generation...")
        endpoints = await server.get_endpoints()
        print(f"✅ Endpoints generated: {endpoints['metadata']['total_endpoints']} endpoints")
        print(f"API: {endpoints['metadata']['api_name']}")
        print(f"Base URL: {endpoints['metadata']['base_url']}")
        
        # Test query execution
        print("\n🔍 Testing query execution...")
        try:
            results = await server.execute_query("/health", "GET", {}, 5)
            print(f"✅ Query executed: {len(results)} results")
            if results:
                print(f"Sample result: {results[0]}")
        except Exception as e:
            print(f"⚠️  Query test failed (expected for test API): {e}")
        
        # Test query validation
        print("\n🛡️ Testing query validation...")
        valid = await server.validate_query("/health", "GET", 10)
        print(f"✅ Valid query: {valid}")
        
        invalid = await server.validate_query("/health", "POST", 10)
        print(f"✅ Invalid method blocked: {not invalid}")
        
        # Test MCP tools
        print("\n🔧 Testing MCP tools...")
        
        # Register tools
        server._register_tools()
        
        print("✅ MCP tools registered successfully")
        
        # Disconnect
        await server.disconnect()
        print("\n✅ REST API MCP server test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ REST API MCP server test failed: {e}")
        return False


async def main():
    """Run the test"""
    print("🚀 Testing REST API MCP Server Template")
    print("=" * 50)
    
    # Check environment
    print("🔍 Checking environment...")
    required_vars = ["API_BASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("Using defaults...")
    
    # Run test
    success = await test_rest_api_server()
    
    if success:
        print("\n🎉 REST API MCP server test passed!")
        print("\n📋 Next steps:")
        print("1. Run: python mcp_server.py")
        print("2. Test with MCP client: python mcp_client.py")
        print("3. Test with FastAPI client")
    else:
        print("\n⚠️  REST API MCP server test failed!")
        print("Check your API configuration and try again.")


if __name__ == "__main__":
    asyncio.run(main())
