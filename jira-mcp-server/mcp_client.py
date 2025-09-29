#!/usr/bin/env python3
"""
JIRA MCP Client

A FastAPI-based MCP client specifically designed for JIRA operations.
Uses fastmcp library to connect to the MCP server via streamable-http transport.

Features:
- JIRA query execution with validation
- Issue search and retrieval
- Project and workflow management
- Health monitoring
- Error handling and logging
- JIRA-specific response models

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
    title="JIRA MCP Client",
    description="FastAPI client for JIRA MCP Server",
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
mcp_client = FastMCP("jira-mcp-client")

# Pydantic Models
class JIRAQuery(BaseModel):
    """JIRA query request model"""
    jql: str = Field(..., description="JIRA Query Language query", example="project = 'PROJ' AND status = 'Open'")
    fields: Optional[List[str]] = Field(None, description="Fields to retrieve")
    limit: Optional[int] = Field(100, description="Maximum number of results", ge=1, le=1000)

class JIRAResponse(BaseModel):
    """JIRA query response model"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    total_results: Optional[int] = None

class WorkflowsResponse(BaseModel):
    """JIRA workflows response model"""
    success: bool
    workflows: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    generated_at: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    jira_url: Optional[str] = None
    auth_type: Optional[str] = None
    connected: Optional[bool] = None
    timestamp: str
    error: Optional[str] = None

class RefreshResponse(BaseModel):
    """Workflows refresh response model"""
    success: bool
    message: str
    generated_at: Optional[str] = None
    total_workflows: Optional[int] = None
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
        "name": "JIRA MCP Client",
        "version": "1.0.0",
        "description": "FastAPI client for JIRA MCP Server",
        "mcp_server_url": MCP_SERVER_URL,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.post("/query", response_model=JIRAResponse)
async def query_jira(query_data: JIRAQuery):
    """
    Execute JIRA query
    
    - **jql**: JIRA Query Language query
    - **fields**: Fields to retrieve
    - **limit**: Maximum number of results (1-1000)
    
    Returns JIRA query results with execution metadata.
    """
    start_time = datetime.utcnow()
    
    try:
        # Call MCP tool
        result = await call_mcp_tool(
            "query_jira",
            jql=query_data.jql,
            fields=json.dumps(query_data.fields or []),
            limit=query_data.limit
        )
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Parse result
        if isinstance(result, str):
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    return JIRAResponse(
                        success=True,
                        data=data,
                        execution_time=execution_time,
                        total_results=len(data)
                    )
                else:
                    return JIRAResponse(
                        success=True,
                        data=[data] if data else [],
                        execution_time=execution_time,
                        total_results=1 if data else 0
                    )
            except json.JSONDecodeError:
                return JIRAResponse(
                    success=False,
                    error=f"Invalid JSON response: {result}",
                    execution_time=execution_time
                )
        else:
            return JIRAResponse(
                success=True,
                data=result if isinstance(result, list) else [result],
                execution_time=execution_time,
                total_results=len(result) if isinstance(result, list) else 1
            )
                
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"JIRA query error: {e}")
        return JIRAResponse(
            success=False,
            error=str(e),
            execution_time=execution_time
        )


@app.get("/workflows", response_model=WorkflowsResponse)
async def get_jira_workflows():
    """
    Get JIRA workflows and metadata
    
    Returns JIRA workflows, projects, and metadata information.
    """
    try:
        # Get MCP resource
        workflows = await get_mcp_resource("workflows://jira")
        
        return WorkflowsResponse(
            success=True,
            workflows=workflows,
            generated_at=workflows.get("metadata", {}).get("generated_at") if isinstance(workflows, dict) else None
        )
        
    except Exception as e:
        logger.error(f"Workflows retrieval error: {e}")
        return WorkflowsResponse(
            success=False,
            error=str(e)
        )


@app.post("/refresh-workflows", response_model=RefreshResponse)
async def refresh_workflows(background_tasks: BackgroundTasks):
    """
    Refresh JIRA workflows cache
    
    Triggers a background refresh of the JIRA workflows cache.
    """
    try:
        # Call MCP tool
        result = await call_mcp_tool("refresh_workflows")
        
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
                message="Workflows refreshed successfully",
                generated_at=result.get("generated_at"),
                total_workflows=result.get("total_workflows")
            )
        else:
            return RefreshResponse(
                success=False,
                error=result.get("error", "Unknown error")
            )
                
    except Exception as e:
        logger.error(f"Workflows refresh error: {e}")
        return RefreshResponse(
            success=False,
            error=str(e)
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check JIRA health
    
    Returns JIRA connection status and health information.
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
            jira_url=health.get("jira_url"),
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
    prompts_obj = await get_mcp_resource("prompts://jira")
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
    logger.info(f"JIRA MCP Client starting on {CLIENT_HOST}:{CLIENT_PORT}")
    logger.info(f"Connected to MCP Server: {MCP_SERVER_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("JIRA MCP Client shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=CLIENT_HOST, port=CLIENT_PORT)
