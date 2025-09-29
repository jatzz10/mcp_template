#!/usr/bin/env python3
"""
FileSystem MCP Client

A FastAPI-based MCP client specifically designed for file system operations.
Uses fastmcp library to connect to the MCP server via streamable-http transport.

Features:
- File system query execution with validation
- Directory structure access
- File search and content reading
- Health monitoring
- Error handling and logging
- File system-specific response models

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
    title="FileSystem MCP Client",
    description="FastAPI client for FileSystem MCP Server",
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
mcp_client = FastMCP("filesystem-mcp-client")

# Pydantic Models
class FileSystemQuery(BaseModel):
    """File system query request model"""
    query_type: str = Field(..., description="Query type: list, search, read, info", example="list")
    path: Optional[str] = Field("", description="File or directory path")
    search_term: Optional[str] = Field("", description="Search term for file search")
    extension: Optional[str] = Field("", description="File extension filter")
    limit: Optional[int] = Field(100, description="Maximum number of results", ge=1, le=1000)

class FileSystemResponse(BaseModel):
    """File system query response model"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    result_count: Optional[int] = None

class StructureResponse(BaseModel):
    """File system structure response model"""
    success: bool
    structure: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    generated_at: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    root_path: Optional[str] = None
    read_access: Optional[bool] = None
    timestamp: str
    error: Optional[str] = None

class RefreshResponse(BaseModel):
    """Structure refresh response model"""
    success: bool
    message: str
    generated_at: Optional[str] = None
    root_path: Optional[str] = None
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
        "name": "FileSystem MCP Client",
        "version": "1.0.0",
        "description": "FastAPI client for FileSystem MCP Server",
        "mcp_server_url": MCP_SERVER_URL,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.post("/query", response_model=FileSystemResponse)
async def query_filesystem(query_data: FileSystemQuery):
    """
    Execute file system query
    
    - **query_type**: Type of query (list, search, read, info)
    - **path**: File or directory path
    - **search_term**: Search term for file search
    - **extension**: File extension filter
    - **limit**: Maximum number of results (1-1000)
    
    Returns file system query results with execution metadata.
    """
    start_time = datetime.utcnow()
    
    try:
        # Call MCP tool
        result = await call_mcp_tool(
            "query_filesystem",
            query_type=query_data.query_type,
            path=query_data.path,
            search_term=query_data.search_term,
            extension=query_data.extension,
            limit=query_data.limit
        )
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Parse result
        if isinstance(result, str):
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    return FileSystemResponse(
                        success=True,
                        data=data,
                        execution_time=execution_time,
                        result_count=len(data)
                    )
                else:
                    return FileSystemResponse(
                        success=True,
                        data=[data] if data else [],
                        execution_time=execution_time,
                        result_count=1 if data else 0
                    )
            except json.JSONDecodeError:
                return FileSystemResponse(
                    success=False,
                    error=f"Invalid JSON response: {result}",
                    execution_time=execution_time
                )
        else:
            return FileSystemResponse(
                success=True,
                data=result if isinstance(result, list) else [result],
                execution_time=execution_time,
                result_count=len(result) if isinstance(result, list) else 1
            )
                
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"File system query error: {e}")
        return FileSystemResponse(
            success=False,
            error=str(e),
            execution_time=execution_time
        )


@app.get("/structure", response_model=StructureResponse)
async def get_filesystem_structure():
    """
    Get file system structure
    
    Returns the complete file system structure including directories and files.
    """
    try:
        # Get MCP resource
        structure = await get_mcp_resource("structure://filesystem")
        
        return StructureResponse(
            success=True,
            structure=structure,
            generated_at=structure.get("metadata", {}).get("generated_at") if isinstance(structure, dict) else None
        )
        
    except Exception as e:
        logger.error(f"Structure retrieval error: {e}")
        return StructureResponse(
            success=False,
            error=str(e)
        )


@app.post("/refresh-structure", response_model=RefreshResponse)
async def refresh_structure(background_tasks: BackgroundTasks):
    """
    Refresh file system structure cache
    
    Triggers a background refresh of the file system structure cache.
    """
    try:
        # Call MCP tool
        result = await call_mcp_tool("refresh_structure")
        
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
                message="Structure refreshed successfully",
                generated_at=result.get("generated_at"),
                root_path=result.get("root_path")
            )
        else:
            return RefreshResponse(
                success=False,
                error=result.get("error", "Unknown error")
            )
                
    except Exception as e:
        logger.error(f"Structure refresh error: {e}")
        return RefreshResponse(
            success=False,
            error=str(e)
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check file system health
    
    Returns file system access status and health information.
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
            root_path=health.get("root_path"),
            read_access=health.get("read_access"),
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
    prompts_obj = await get_mcp_resource("prompts://filesystem")
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
    logger.info(f"FileSystem MCP Client starting on {CLIENT_HOST}:{CLIENT_PORT}")
    logger.info(f"Connected to MCP Server: {MCP_SERVER_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("FileSystem MCP Client shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=CLIENT_HOST, port=CLIENT_PORT)
