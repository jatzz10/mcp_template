#!/usr/bin/env python3
"""
Test script for Database MCP Server
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp_server import DatabaseMCPServer


async def test_database_server():
    """Test the database MCP server"""
    print("🧪 Testing Database MCP Server")
    print("=" * 40)
    
    # Load configuration from environment
    config = {
        'server_name': 'test-db-server',
        'server_host': '127.0.0.1',
        'server_port': 8002,  # Use different port for testing
        'db_type': os.getenv('DB_TYPE', 'mysql'),
        'db_host': os.getenv('DB_HOST', 'localhost'),
        'db_port': int(os.getenv('DB_PORT', '3306')),
        'db_user': os.getenv('DB_USER', 'root'),
        'db_password': os.getenv('DB_PASSWORD', ''),
        'db_name': os.getenv('DB_NAME', 'test_db'),
        'db_path': os.getenv('DB_PATH', ''),
        'log_level': 'INFO',
        'schema_cache_ttl': 3600,
        'query_cache_ttl': 300,
        'max_query_limit': 1000
    }
    
    print(f"📊 Database Type: {config['db_type'].upper()}")
    print(f"🔗 Connection: {config['db_user']}@{config['db_host']}:{config['db_port']}/{config['db_name']}")
    
    try:
        # Create server
        server = DatabaseMCPServer(config)
        
        # Test connection
        print("\n🔌 Testing database connection...")
        connected = await server.connect()
        if not connected:
            print("❌ Failed to connect to database")
            return False
        print("✅ Connected to database")
        
        # Test health check
        print("\n🏥 Testing health check...")
        health = await server.health_check()
        print(f"Health: {health['status']}")
        
        # Test schema generation
        print("\n📋 Testing schema generation...")
        schema = await server.get_schema()
        print(f"✅ Schema generated: {schema['metadata']['total_tables']} tables")
        print(f"Database: {schema['metadata']['database_name']}")
        print(f"Type: {schema['metadata']['database_type']}")
        
        # Test query execution
        print("\n🔍 Testing query execution...")
        results = await server.execute_query("SELECT 1 as test_column, 'Hello Database!' as message", 5)
        print(f"✅ Query executed: {len(results)} results")
        print(f"Sample result: {results[0]}")
        
        # Test query validation
        print("\n🛡️ Testing query validation...")
        valid = await server.validate_query("SELECT * FROM users LIMIT 5", 10)
        print(f"✅ Valid query: {valid}")
        
        invalid = await server.validate_query("DROP TABLE users", 10)
        print(f"✅ Invalid query blocked: {not invalid}")
        
        # Test MCP tools
        print("\n🔧 Testing MCP tools...")
        
        # Test query_database tool
        from fastmcp import FastMCP
        mcp = FastMCP("test")
        
        # Register tools
        server._register_tools()
        
        print("✅ MCP tools registered successfully")
        
        # Disconnect
        await server.disconnect()
        print("\n✅ Database MCP server test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database MCP server test failed: {e}")
        return False


async def main():
    """Run the test"""
    print("🚀 Testing Database MCP Server Template")
    print("=" * 50)
    
    # Check environment
    print("🔍 Checking environment...")
    required_vars = ["DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("Using defaults...")
    
    # Run test
    success = await test_database_server()
    
    if success:
        print("\n🎉 Database MCP server test passed!")
        print("\n📋 Next steps:")
        print("1. Run: python mcp_server.py")
        print("2. Test with MCP client")
        print("3. Test with FastAPI client")
    else:
        print("\n⚠️  Database MCP server test failed!")
        print("Check your database configuration and try again.")


if __name__ == "__main__":
    asyncio.run(main())
