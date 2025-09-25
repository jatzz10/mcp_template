#!/usr/bin/env python3
"""
Example REST API MCP Server using the template
"""

import asyncio
import os
from template.mcp_server.base import MCPServer
from template.mcp_server.datasources.rest_api import RestAPIDataSource


async def main():
    """Create and run a REST API MCP server"""
    
    # Configuration
    config = {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 8001,
        "cache": {
            "query_cache_size": 1000,
            "query_cache_ttl": 300,
            "schema_cache_size": 100,
            "schema_cache_ttl": 3600
        }
    }
    
    # Create server
    server = MCPServer("rest-api-mcp-server", config)
    
    # Add REST API data sources
    # Example 1: JSONPlaceholder API
    jsonplaceholder_config = {
        "base_url": "https://jsonplaceholder.typicode.com",
        "auth_type": "none",
        "timeout": 30,
        "rate_limit": 100,
        "schema_cache_ttl": 3600,
        "query_cache_ttl": 300,
        "max_query_limit": 1000
    }
    
    jsonplaceholder_ds = RestAPIDataSource("jsonplaceholder", jsonplaceholder_config)
    server.add_data_source("jsonplaceholder", jsonplaceholder_ds)
    
    # Example 2: GitHub API (if token provided)
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        github_config = {
            "base_url": "https://api.github.com",
            "auth_type": "bearer",
            "auth_token": github_token,
            "timeout": 30,
            "rate_limit": 60,  # GitHub has stricter rate limits
            "schema_cache_ttl": 3600,
            "query_cache_ttl": 300,
            "max_query_limit": 1000
        }
        
        github_ds = RestAPIDataSource("github", github_config)
        server.add_data_source("github", github_ds)
    
    # Example 3: Custom API with API key
    custom_api_key = os.getenv("CUSTOM_API_KEY")
    custom_api_url = os.getenv("CUSTOM_API_URL")
    if custom_api_key and custom_api_url:
        custom_config = {
            "base_url": custom_api_url,
            "auth_type": "api_key",
            "api_key": custom_api_key,
            "api_key_header": "X-API-Key",
            "timeout": 30,
            "rate_limit": 100,
            "schema_cache_ttl": 3600,
            "query_cache_ttl": 300,
            "max_query_limit": 1000
        }
        
        custom_ds = RestAPIDataSource("custom_api", custom_config)
        server.add_data_source("custom_api", custom_ds)
    
    # Start server
    print("🚀 Starting REST API MCP Server")
    print(f"📊 Data sources: {list(server.data_sources.keys())}")
    print(f"🌐 Server URL: http://{config['host']}:{config['port']}/mcp")
    
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
