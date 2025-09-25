#!/usr/bin/env python3
"""
Example FastAPI MCP Client using the template
"""

import uvicorn
from template.mcp_client.fastapi import MCPFastAPIClient

# Optional: Import your LLM client
try:
    from nail_client.nail_llm_langchain import NailLLMLangchain
    llm_client = NailLLMLangchain(
        model_id="claude-3.5",
        temperature=0.2,
        max_tokens=600,
        api_key="your_api_key_here"
    )
except ImportError:
    llm_client = None
    print("⚠️  LLM client not available. Natural language queries will be disabled.")


def main():
    """Create and run a FastAPI MCP client"""
    
    # Configuration
    config = {
        "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
        "timeout": 30
    }
    
    # Create FastAPI client
    mcp_client = MCPFastAPIClient(
        server_url="http://127.0.0.1:8000/mcp",  # Your MCP server URL
        llm_client=llm_client,
        config=config
    )
    
    # Get FastAPI app
    app = mcp_client.get_app()
    
    # Add custom routes if needed
    @app.get("/")
    async def root():
        return {
            "message": "MCP FastAPI Client",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "tools": "/tools",
                "resources": "/resources",
                "query": "/query",
                "ask": "/ask",
                "schema": "/schema",
                "data_sources": "/data-sources"
            }
        }
    
    # Run the server
    print("🚀 Starting FastAPI MCP Client")
    print("📋 Available endpoints:")
    print("  GET  /health          - Health check")
    print("  GET  /tools           - List MCP tools")
    print("  GET  /resources       - List MCP resources")
    print("  POST /query           - Execute direct query")
    print("  POST /ask             - Natural language query")
    print("  GET  /schema          - Get schema")
    print("  GET  /data-sources    - List data sources")
    print("🌐 Server URL: http://127.0.0.1:3000")
    
    uvicorn.run(app, host="127.0.0.1", port=3000)


if __name__ == "__main__":
    main()
