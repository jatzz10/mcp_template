#!/usr/bin/env python3
"""
REST API MCP Client

A FastAPI-based MCP client specifically designed for REST API operations.
Uses fastmcp library to connect to the MCP server via streamable-http transport.

Features:
- API query execution with validation
- Endpoint discovery and documentation
- Health monitoring
- Error handling and logging
- API-specific response models

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
from fastmcp import FastMCP
try:
    from nail_client.nail_llm_langchain import NailLLMLangchain  # type: ignore
    HAS_NAIL_LLM = True
except Exception:
    HAS_NAIL_LLM = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="REST API MCP Client",
    description="FastAPI client for REST API MCP Server",
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
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
CLIENT_HOST = os.getenv("CLIENT_HOST", "0.0.0.0")
CLIENT_PORT = int(os.getenv("CLIENT_PORT", "8001"))

# MCP Client
mcp_client = FastMCP("rest-api-mcp-client")

# Pydantic Models
class APIQuery(BaseModel):
    """API query request model"""
    endpoint: str = Field(..., description="API endpoint to query", example="/users")
    method: str = Field("GET", description="HTTP method", example="GET")
    params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")
    limit: Optional[int] = Field(100, description="Maximum number of results", ge=1, le=1000)

class APIResponse(BaseModel):
    """API query response model"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    response_size: Optional[int] = None

class EndpointsResponse(BaseModel):
    """API endpoints response model"""
    success: bool
    endpoints: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    total_endpoints: Optional[int] = None
    generated_at: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    api_base_url: Optional[str] = None
    auth_type: Optional[str] = None
    connected: Optional[bool] = None
    timestamp: str
    error: Optional[str] = None

class RefreshResponse(BaseModel):
    """Endpoints refresh response model"""
    success: bool
    message: str
    generated_at: Optional[str] = None
    total_endpoints: Optional[int] = None
    error: Optional[str] = None


# /ask_llm models
class AskLLMRequest(BaseModel):
    question: str

class AskLLMResponse(BaseModel):
    success: bool
    action: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None

# MCP Client Functions
async def call_mcp_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Call MCP tool on the server"""
    try:
        # Connect to MCP server
        await mcp_client.connect(MCP_SERVER_URL, transport="streamable-http")
        
        # Call the tool
        result = await mcp_client.call_tool(tool_name, **kwargs)
        
        # Disconnect
        await mcp_client.disconnect()
        
        return result
    except Exception as e:
        logger.error(f"MCP tool call failed: {e}")
        raise

async def get_mcp_resource(resource_uri: str) -> Dict[str, Any]:
    """Get MCP resource from the server"""
    try:
        # Connect to MCP server
        await mcp_client.connect(MCP_SERVER_URL, transport="streamable-http")
        
        # Get the resource
        result = await mcp_client.get_resource(resource_uri)
        
        # Disconnect
        await mcp_client.disconnect()
        
        return result
    except Exception as e:
        logger.error(f"MCP resource call failed: {e}")
        raise


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "REST API MCP Client",
        "version": "1.0.0",
        "description": "FastAPI client for REST API MCP Server",
        "mcp_server_url": MCP_SERVER_URL,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.post("/query", response_model=APIResponse)
async def query_api(query_data: APIQuery):
    """
    Execute API query
    
    - **endpoint**: API endpoint to query
    - **method**: HTTP method (GET, HEAD, OPTIONS)
    - **params**: Query parameters
    - **limit**: Maximum number of results (1-1000)
    
    Returns API response data with execution metadata.
    """
    start_time = datetime.utcnow()
    
    try:
        # Call MCP tool
        result = await call_mcp_tool(
            "query_api", 
            endpoint=query_data.endpoint,
            method=query_data.method,
            params=json.dumps(query_data.params or {}),
            limit=query_data.limit
        )
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Parse result
        if isinstance(result, str):
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    return APIResponse(
                        success=True,
                        data=data,
                        execution_time=execution_time,
                        response_size=len(data)
                    )
                else:
                    return APIResponse(
                        success=True,
                        data=[data] if data else [],
                        execution_time=execution_time,
                        response_size=1 if data else 0
                    )
            except json.JSONDecodeError:
                return APIResponse(
                    success=False,
                    error=f"Invalid JSON response: {result}",
                    execution_time=execution_time
                )
        else:
            return APIResponse(
                success=True,
                data=result if isinstance(result, list) else [result],
                execution_time=execution_time,
                response_size=len(result) if isinstance(result, list) else 1
            )
                
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"API query error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            execution_time=execution_time
        )


@app.get("/endpoints", response_model=EndpointsResponse)
async def get_api_endpoints():
    """
    Get API endpoints documentation
    
    Returns discovered API endpoints with descriptions and sample responses.
    """
    try:
        # Get MCP resource
        endpoints_data = await get_mcp_resource("endpoints://api")
        
        if isinstance(endpoints_data, dict):
            endpoints = endpoints_data.get("endpoints", [])
            metadata = endpoints_data.get("metadata", {})
            
            return EndpointsResponse(
                success=True,
                endpoints=endpoints,
                total_endpoints=len(endpoints),
                generated_at=metadata.get("generated_at")
            )
        else:
            return EndpointsResponse(
                success=True,
                endpoints=[],
                total_endpoints=0
            )
            
    except Exception as e:
        logger.error(f"Endpoints retrieval error: {e}")
        return EndpointsResponse(
            success=False,
            error=str(e)
        )


@app.post("/refresh-endpoints", response_model=RefreshResponse)
async def refresh_endpoints(background_tasks: BackgroundTasks):
    """
    Refresh API endpoints cache
    
    Triggers a background refresh of the API endpoints cache.
    """
    try:
        # Call MCP tool
        result = await call_mcp_tool("refresh_endpoints")
        
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
                message="Endpoints refreshed successfully",
                generated_at=result.get("generated_at"),
                total_endpoints=result.get("total_endpoints")
            )
        else:
            return RefreshResponse(
                success=False,
                error=result.get("error", "Unknown error")
            )
                
    except Exception as e:
        logger.error(f"Endpoints refresh error: {e}")
        return RefreshResponse(
            success=False,
            error=str(e)
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check API health
    
    Returns API connection status and health information.
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
            api_base_url=health.get("api_base_url"),
            auth_type=health.get("auth_type"),
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


def get_llm() -> "NailLLMLangchain | None":
    if not HAS_NAIL_LLM:
        return None
    try:
        return NailLLMLangchain(
            model_id=os.getenv("NAIL_LLM_MODEL_ID", "claude-3.5"),
            temperature=float(os.getenv("NAIL_LLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("NAIL_LLM_MAX_TOKENS", "600")),
            api_key=os.getenv("NAIL_LLM_API_KEY", ""),
        )
    except Exception:
        return None

async def get_prompts_resource() -> str:
    prompts_obj = await get_mcp_resource("prompts://rest-api")
    return json.dumps(prompts_obj) if isinstance(prompts_obj, (dict, list)) else str(prompts_obj)

@app.post("/ask_llm", response_model=AskLLMResponse)
async def ask_llm(payload: AskLLMRequest):
    llm = get_llm()
    if llm is None:
        return AskLLMResponse(success=False, error="LLM not configured. Set NAIL_LLM_API_KEY.")
    try:
        prompts_text = await get_prompts_resource()
        prompt = prompts_text + "\n\nUser question: " + payload.question
        raw = llm.invoke(prompt)
        try:
            action = json.loads(raw)
        except Exception:
            return AskLLMResponse(success=False, error="LLM did not return valid JSON action", result=raw)
        act = (action or {}).get("action")
        if act == "read_resource":
            uri = action.get("uri", "")
            res = await get_mcp_resource(uri)
            return AskLLMResponse(success=True, action=action, result=res)
        if act == "call_tool":
            tool = action.get("tool", "")
            args = action.get("args", {})
            res = await call_mcp_tool(tool, **args)
            return AskLLMResponse(success=True, action=action, result=res)
        return AskLLMResponse(success=False, error="Unsupported or missing action", action=action)
    except Exception as e:
        logger.exception("/ask_llm error")
        return AskLLMResponse(success=False, error=str(e))


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info(f"REST API MCP Client starting on {CLIENT_HOST}:{CLIENT_PORT}")
    logger.info(f"Connected to MCP Server: {MCP_SERVER_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("REST API MCP Client shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=CLIENT_HOST, port=CLIENT_PORT)
