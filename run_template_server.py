#!/usr/bin/env python3
"""
Run the template MCP server with your current MySQL setup
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


async def main():
    """Run the template MCP server"""
    
    print("🚀 Starting Template MCP Server with MySQL")
    print("=" * 50)
    
    # Server configuration
    config = {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 8002,  # Different port to avoid conflicts
        "cache": {
            "query_cache_size": 1000,
            "query_cache_ttl": 300,
            "schema_cache_size": 100,
            "schema_cache_ttl": 3600
        }
    }
    
    # MySQL configuration (using your current setup)
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
    
    print(f"📊 MySQL Config: {mysql_config['user']}@{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}")
    
    # Create server
    server = MCPServer("template-mysql-server", config)
    
    # Add MySQL data source
    mysql_ds = MySQLDataSource("mysql", mysql_config)
    server.add_data_source("mysql", mysql_ds)
    
    print(f"✅ Server created with data sources: {list(server.data_sources.keys())}")
    print(f"🌐 Server URL: http://{config['host']}:{config['port']}/mcp")
    print("\n📋 Available tools:")
    print("  - query_mysql: Execute SQL queries")
    print("  - refresh_schema: Refresh database schema")
    print("  - list_data_sources: List available data sources")
    print("  - health_check: Check server health")
    print("\n📄 Available resources:")
    print("  - mysql://schema: Database schema")
    print("  - server://info: Server information")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Start server
        await server.start()
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
