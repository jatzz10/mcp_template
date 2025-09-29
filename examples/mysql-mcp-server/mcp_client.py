#!/usr/bin/env python3
"""
Database MCP Client

A FastAPI-based MCP client specifically designed for database operations.
Uses fastmcp library to connect to the MCP server via streamable-http transport.

Features:
- SQL query execution with validation
- Database schema access
- Health monitoring
- Error handling and logging
- Database-specific response models

Usage:
    uvicorn mcp_client:app --host 0.0.0.0 --port 8001

Environment Variables:
    MCP_SERVER_URL=http://localhost:8000
    CLIENT_HOST=0.0.0.0
    CLIENT_PORT=8001
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import asyncio
import json
import os
import logging
from datetime import datetime
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Database MCP Client",
    description="FastAPI client for Database MCP Server",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
CLIENT_HOST = os.getenv("CLIENT_HOST", "0.0.0.0")
CLIENT_PORT = int(os.getenv("CLIENT_PORT", "8001"))

def _normalize_server_url(url: str) -> str:
    url = url.strip().rstrip("/")
    return url if url.endswith("/mcp") else url + "/mcp"

# Pydantic Models
class DatabaseQuery(BaseModel):
    """Database query request model"""
    query: str = Field(..., description="SQL query to execute", example="SELECT * FROM users LIMIT 10")
    limit: Optional[int] = Field(100, description="Maximum number of results", ge=1, le=1000)

class DatabaseResponse(BaseModel):
    """Database query response model"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    row_count: Optional[int] = None

class SchemaResponse(BaseModel):
    """Database schema response model"""
    success: bool
    schema: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    generated_at: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    database_type: Optional[str] = None
    connected: Optional[bool] = None
    timestamp: str
    error: Optional[str] = None

class RefreshResponse(BaseModel):
    """Schema refresh response model"""
    success: bool
    message: str
    generated_at: Optional[str] = None
    total_tables: Optional[int] = None
    error: Optional[str] = None


# MCP Client Functions
async def call_mcp_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Call MCP tool on the server using FastMCP client"""
    server_url = _normalize_server_url(MCP_SERVER_URL)
    transport = StreamableHttpTransport(url=server_url)
    client = Client(transport)
    await client.__aenter__()
    try:
        result = await client.call_tool(tool_name, kwargs)
        # Extract common result shapes
        if hasattr(result, 'content') and result.content:
            text = result.content[0].text
            try:
                return json.loads(text)
            except Exception:
                return text  # plain text
        return {}
    finally:
        await client.__aexit__(None, None, None)

async def get_mcp_resource(resource_uri: str) -> Dict[str, Any]:
    """Get MCP resource from the server using FastMCP client"""
    server_url = _normalize_server_url(MCP_SERVER_URL)
    transport = StreamableHttpTransport(url=server_url)
    client = Client(transport)
    await client.__aenter__()
    try:
        resource = await client.read_resource(resource_uri)
        # FastMCP returns contents list
        if hasattr(resource, 'contents') and resource.contents:
            text = resource.contents[0].text
            try:
                return json.loads(text)
            except Exception:
                return text
        return {}
    finally:
        await client.__aexit__(None, None, None)


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Database MCP Client",
        "version": "1.0.0",
        "description": "FastAPI client for Database MCP Server",
        "mcp_server_url": MCP_SERVER_URL,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.post("/query", response_model=DatabaseResponse)
async def query_database(query_data: DatabaseQuery):
    """
    Execute SQL query against the database
    
    - **query**: SQL query to execute (SELECT only)
    - **limit**: Maximum number of results (1-1000)
    
    Returns query results with execution metadata.
    """
    start_time = datetime.utcnow()
    
    try:
        # Call MCP tool
        result = await call_mcp_tool("query_database", query=query_data.query, limit=query_data.limit)
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Parse result
        if isinstance(result, str):
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    return DatabaseResponse(
                        success=True,
                        data=data,
                        execution_time=execution_time,
                        row_count=len(data)
                    )
                else:
                    return DatabaseResponse(
                        success=True,
                        data=[data] if data else [],
                        execution_time=execution_time,
                        row_count=1 if data else 0
                    )
            except json.JSONDecodeError:
                return DatabaseResponse(
                    success=False,
                    error=f"Invalid JSON response: {result}",
                    execution_time=execution_time
                )
        else:
            return DatabaseResponse(
                success=True,
                data=result if isinstance(result, list) else [result],
                execution_time=execution_time,
                row_count=len(result) if isinstance(result, list) else 1
            )
                
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"Database query error: {e}")
        return DatabaseResponse(
            success=False,
            error=str(e),
            execution_time=execution_time
        )


@app.get("/schema", response_model=SchemaResponse)
async def get_database_schema():
    """
    Get complete database schema
    
    Returns database schema including tables, columns, indexes, and relationships.
    """
    try:
        # Get MCP resource
        schema = await get_mcp_resource("schema://database")
        
        return SchemaResponse(
            success=True,
            schema=schema,
            generated_at=schema.get("metadata", {}).get("generated_at") if isinstance(schema, dict) else None
        )
        
    except Exception as e:
        logger.error(f"Schema retrieval error: {e}")
        return SchemaResponse(
            success=False,
            error=str(e)
        )


@app.post("/refresh-schema", response_model=RefreshResponse)
async def refresh_schema(background_tasks: BackgroundTasks):
    """
    Refresh database schema cache
    
    Triggers a background refresh of the database schema cache.
    """
    try:
        # Call MCP tool
        result = await call_mcp_tool("refresh_schema")
        
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                return RefreshResponse(
                    success=False,
                    error=f"Invalid JSON response: {result}"
                )
        
        if result.get("status") == "success":
            return RefreshResponse(
                success=True,
                message="Schema refreshed successfully",
                generated_at=result.get("generated_at"),
                total_tables=result.get("total_tables")
            )
        else:
            return RefreshResponse(
                success=False,
                error=result.get("error", "Unknown error")
            )
                
    except Exception as e:
        logger.error(f"Schema refresh error: {e}")
        return RefreshResponse(
            success=False,
            error=str(e)
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check database health
    
    Returns database connection status and health information.
    """
    try:
        # Call MCP tool
        health = await call_mcp_tool("health_check")
        
        if isinstance(health, str):
            try:
                health = json.loads(health)
            except json.JSONDecodeError:
                return HealthResponse(
                    status="error",
                    error=f"Invalid JSON response: {health}",
                    timestamp=datetime.utcnow().isoformat()
                )
        
        return HealthResponse(
            status=health.get("status", "unknown"),
            database_type=health.get("database_type"),
            connected=health.get("connected"),
            timestamp=health.get("timestamp", datetime.utcnow().isoformat()),
            error=health.get("error")
        )
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            status="error",
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info(f"Database MCP Client starting on {CLIENT_HOST}:{CLIENT_PORT}")
    logger.info(f"Connected to MCP Server: {MCP_SERVER_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("Database MCP Client shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=CLIENT_HOST, port=CLIENT_PORT)
