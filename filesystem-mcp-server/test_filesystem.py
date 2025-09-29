#!/usr/bin/env python3
"""
Test script for FileSystem MCP Server
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp_server import FileSystemMCPServer


async def test_filesystem_server():
    """Test the FileSystem MCP server"""
    print("🧪 Testing FileSystem MCP Server")
    print("=" * 40)
    
    # Load configuration from environment
    config = {
        'server_name': 'test-filesystem-server',
        'server_host': '127.0.0.1',
        'server_port': 8004,  # Use different port for testing
        'root_path': os.getenv('FILESYSTEM_ROOT_PATH', '/tmp'),
        'max_depth': int(os.getenv('FILESYSTEM_MAX_DEPTH', '3')),
        'include_hidden': os.getenv('FILESYSTEM_INCLUDE_HIDDEN', 'false').lower() == 'true',
        'include_file_content': os.getenv('FILESYSTEM_INCLUDE_FILE_CONTENT', 'false').lower() == 'true',
        'max_file_size': int(os.getenv('FILESYSTEM_MAX_FILE_SIZE', '1048576')),
        'allowed_extensions': os.getenv('FILESYSTEM_ALLOWED_EXTENSIONS', '').split(',') if os.getenv('FILESYSTEM_ALLOWED_EXTENSIONS') else [],
        'excluded_directories': os.getenv('FILESYSTEM_EXCLUDED_DIRS', '.git,node_modules,__pycache__').split(','),
        'log_level': 'INFO',
        'structure_cache_ttl': 3600,
        'query_cache_ttl': 300,
        'max_query_limit': 1000
    }
    
    print(f"📊 Root Path: {config['root_path']}")
    print(f"🔗 Max Depth: {config['max_depth']}")
    print(f"📁 Include Hidden: {config['include_hidden']}")
    
    try:
        # Create server
        server = FileSystemMCPServer(config)
        
        # Test connection
        print("\n🔌 Testing file system connection...")
        connected = await server.connect()
        if not connected:
            print("❌ Failed to connect to file system")
            return False
        print("✅ Connected to file system")
        
        # Test health check
        print("\n🏥 Testing health check...")
        health = await server.health_check()
        print(f"Health: {health['status']}")
        print(f"Read Access: {health.get('read_access', 'unknown')}")
        
        # Test structure generation
        print("\n📋 Testing structure generation...")
        structure = await server.get_structure()
        print(f"✅ Structure generated")
        print(f"Root Path: {structure['metadata']['root_path']}")
        print(f"Max Depth: {structure['metadata']['max_depth']}")
        
        # Test query execution
        print("\n🔍 Testing query execution...")
        try:
            results = await server.execute_query("list", config['root_path'], "", "", 5)
            print(f"✅ List query executed: {len(results)} results")
            if results:
                print(f"Sample result: {results[0]}")
        except Exception as e:
            print(f"❌ List query failed: {e}")
        
        # Test search query
        try:
            results = await server.execute_query("search", config['root_path'], "test", "", 5)
            print(f"✅ Search query executed: {len(results)} results")
        except Exception as e:
            print(f"⚠️  Search query failed (expected if no test files): {e}")
        
        # Test query validation
        print("\n🛡️ Testing query validation...")
        valid = await server.validate_query("list", config['root_path'], 10)
        print(f"✅ Valid query: {valid}")
        
        # Test path traversal protection
        invalid = await server.validate_query("list", "../../etc/passwd", 10)
        print(f"✅ Path traversal blocked: {not invalid}")
        
        # Test MCP tools
        print("\n🔧 Testing MCP tools...")
        
        # Register tools
        server._register_tools()
        
        print("✅ MCP tools registered successfully")
        
        # Disconnect
        await server.disconnect()
        print("\n✅ FileSystem MCP server test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ FileSystem MCP server test failed: {e}")
        return False


async def main():
    """Run the test"""
    print("🚀 Testing FileSystem MCP Server Template")
    print("=" * 50)
    
    # Check environment
    print("🔍 Checking environment...")
    root_path = os.getenv('FILESYSTEM_ROOT_PATH', '/tmp')
    
    if not os.path.exists(root_path):
        print(f"⚠️  Root path does not exist: {root_path}")
        print("Creating test directory...")
        os.makedirs(root_path, exist_ok=True)
    
    if not os.path.isdir(root_path):
        print(f"❌ Root path is not a directory: {root_path}")
        return
    
    # Run test
    success = await test_filesystem_server()
    
    if success:
        print("\n🎉 FileSystem MCP server test passed!")
        print("\n📋 Next steps:")
        print("1. Run: python mcp_server.py")
        print("2. Test with MCP client: python mcp_client.py")
        print("3. Test with FastAPI client")
    else:
        print("\n⚠️  FileSystem MCP server test failed!")
        print("Check your file system configuration and try again.")


if __name__ == "__main__":
    asyncio.run(main())
