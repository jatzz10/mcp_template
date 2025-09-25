#!/usr/bin/env python3
"""
Example MySQL MCP Server using the template
"""

import asyncio
import os
from template.mcp_server.base import MCPServer
from template.mcp_server.datasources.mysql import MySQLDataSource


async def main():
    """Create and run a MySQL MCP server"""
    
    # Configuration
    config = {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 8000,
        "cache": {
            "query_cache_size": 1000,
            "query_cache_ttl": 300,
            "schema_cache_size": 100,
            "schema_cache_ttl": 3600
        }
    }
    
    # Create server
    server = MCPServer("mysql-mcp-server", config)
    
    # Add MySQL data source
    mysql_config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "test"),
        "schema_cache_ttl": 3600,
        "query_cache_ttl": 300,
        "max_query_limit": 1000
    }
    
    mysql_ds = MySQLDataSource("mysql", mysql_config)
    server.add_data_source("mysql", mysql_ds)
    
    # Start server
    print("🚀 Starting MySQL MCP Server")
    print(f"📊 Data sources: {list(server.data_sources.keys())}")
    print(f"🌐 Server URL: http://{config['host']}:{config['port']}/mcp")
    
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
