#!/usr/bin/env python3
"""
Test script to verify the template works with your current MySQL setup
"""

import asyncio
import os
import sys
from pathlib import Path

# Add template to path
template_path = Path(__file__).parent
sys.path.insert(0, str(template_path))

from mcp_server.base import MCPServer
from mcp_server.datasources.mysql import MySQLDataSource


async def test_mysql_datasource():
    """Test MySQL data source with your current setup"""
    print("🧪 Testing MySQL Data Source...")
    
    # Use your current environment variables
    mysql_config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "mcp_test"),
        "password": os.getenv("MYSQL_PASSWORD", "mcp_test_password"),
        "database": os.getenv("MYSQL_DATABASE", "mcp_test_db"),
        "schema_cache_ttl": 3600,
        "query_cache_ttl": 300,
        "max_query_limit": 1000
    }
    
    print(f"📊 Config: {mysql_config['user']}@{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}")
    
    # Create MySQL data source
    mysql_ds = MySQLDataSource("mysql", mysql_config)
    
    try:
        # Test connection
        print("🔌 Testing connection...")
        connected = await mysql_ds.connect()
        if not connected:
            print("❌ Failed to connect to MySQL")
            return False
        print("✅ Connected to MySQL")
        
        # Test health check
        print("🏥 Testing health check...")
        health = await mysql_ds.health_check()
        print(f"Health: {health['status']}")
        
        # Test schema generation
        print("📋 Testing schema generation...")
        schema = await mysql_ds.get_schema()
        print(f"✅ Schema generated: {schema['metadata']['total_tables']} tables")
        
        # Test query execution
        print("🔍 Testing query execution...")
        results = await mysql_ds.query({"query": "SELECT 1 as test_column, 'Hello Template!' as message", "limit": 5})
        print(f"✅ Query executed: {len(results)} results")
        print(f"Sample result: {results[0]}")
        
        # Test query validation
        print("🛡️ Testing query validation...")
        valid = await mysql_ds.validate_query({"query": "SELECT * FROM users LIMIT 5", "limit": 10})
        print(f"✅ Valid query: {valid}")
        
        invalid = await mysql_ds.validate_query({"query": "DROP TABLE users", "limit": 10})
        print(f"✅ Invalid query blocked: {not invalid}")
        
        # Disconnect
        await mysql_ds.disconnect()
        print("✅ MySQL data source test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ MySQL data source test failed: {e}")
        return False


async def test_mcp_server():
    """Test MCP server with MySQL data source"""
    print("\n🧪 Testing MCP Server...")
    
    # Server configuration
    config = {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 8002,  # Use different port to avoid conflicts
        "cache": {
            "query_cache_size": 100,
            "query_cache_ttl": 300,
            "schema_cache_size": 50,
            "schema_cache_ttl": 3600
        }
    }
    
    # MySQL configuration
    mysql_config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "mcp_test"),
        "password": os.getenv("MYSQL_PASSWORD", "mcp_test_password"),
        "database": os.getenv("MYSQL_DATABASE", "mcp_test_db"),
        "schema_cache_ttl": 3600,
        "query_cache_ttl": 300,
        "max_query_limit": 1000
    }
    
    try:
        # Create server
        server = MCPServer("test-mysql-server", config)
        
        # Add MySQL data source
        mysql_ds = MySQLDataSource("mysql", mysql_config)
        server.add_data_source("mysql", mysql_ds)
        
        print("✅ MCP server created with MySQL data source")
        print(f"📊 Data sources: {list(server.data_sources.keys())}")
        print(f"🌐 Server would run on: http://{config['host']}:{config['port']}/mcp")
        
        # Test server info
        server_info = server.get_server_info()
        print(f"✅ Server info: {server_info}")
        
        print("✅ MCP server test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False


async def test_fastapi_client():
    """Test FastAPI client (without actually starting server)"""
    print("\n🧪 Testing FastAPI Client...")
    
    try:
        from mcp_client.fastapi import MCPFastAPIClient
        
        # Create client (won't connect since server isn't running)
        client = MCPFastAPIClient(
            server_url="http://127.0.0.1:8002/mcp",
            llm_client=None,  # No LLM for this test
            config={"cors_origins": ["*"]}
        )
        
        # Get FastAPI app
        app = client.get_app()
        
        print("✅ FastAPI client created successfully")
        print("📋 Available endpoints:")
        print("  GET  /health")
        print("  GET  /tools")
        print("  GET  /resources")
        print("  POST /query")
        print("  POST /ask")
        print("  GET  /schema")
        print("  GET  /data-sources")
        
        print("✅ FastAPI client test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ FastAPI client test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Testing MCP Template with Current MySQL Setup")
    print("=" * 60)
    
    # Check environment
    print("🔍 Checking environment...")
    required_vars = ["MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("Using defaults from your current setup...")
    
    # Run tests
    tests = [
        ("MySQL Data Source", test_mysql_datasource),
        ("MCP Server", test_mcp_server),
        ("FastAPI Client", test_fastapi_client)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 All tests passed! Template is ready to use.")
        print("\n📋 Next steps:")
        print("1. Run: python run_template_server.py")
        print("2. Run: python test_template_client.py")
        print("3. Run: python examples/fastapi_client.py")
        print("4. Test the REST API endpoints")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
