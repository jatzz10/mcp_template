"""
FastAPI MCP Client implementation
"""

from typing import Dict, Any, Optional, List
import json
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .base import MCPClientBase


class QueryRequest(BaseModel):
    """Request model for database queries"""
    query: str = Field(..., description="SQL query to execute")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    data_source: Optional[str] = Field(default=None, description="Specific data source to query")


class NaturalLanguageRequest(BaseModel):
    """Request model for natural language queries"""
    question: str = Field(..., description="Natural language question")
    data_source: Optional[str] = Field(default=None, description="Specific data source to query")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")


class SchemaRequest(BaseModel):
    """Request model for schema requests"""
    data_source: Optional[str] = Field(default=None, description="Specific data source")


class MCPFastAPIClient:
    """
    FastAPI-based MCP client that provides REST endpoints for MCP server interaction.
    
    Features:
    - REST API endpoints for MCP tools and resources
    - Natural language query processing (with LLM integration)
    - Schema management
    - Health monitoring
    - CORS support
    """
    
    def __init__(
        self,
        server_url: str,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.server_url = server_url
        self.llm_client = llm_client
        self.config = config or {}
        self.mcp_client = MCPClientBase(server_url, config)
        self.logger = logging.getLogger("mcp_fastapi_client")
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="MCP FastAPI Client",
            description="REST API client for Model Context Protocol servers",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes"""
        
        @self.app.on_event("startup")
        async def startup_event():
            """Initialize MCP connection on startup"""
            await self.mcp_client.connect()
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Close MCP connection on shutdown"""
            await self.mcp_client.disconnect()
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            health = await self.mcp_client.health_check()
            if health["status"] != "healthy":
                raise HTTPException(status_code=503, detail=health)
            return health
        
        @self.app.get("/tools")
        async def list_tools():
            """List available MCP tools"""
            try:
                tools = await self.mcp_client.list_tools()
                return {"tools": tools}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/resources")
        async def list_resources():
            """List available MCP resources"""
            try:
                resources = await self.mcp_client.list_resources()
                return {"resources": resources}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/query")
        async def execute_query(request: QueryRequest):
            """Execute a direct query"""
            try:
                # Determine tool name based on data source
                tool_name = f"query_{request.data_source}" if request.data_source else "query_mysql"
                
                result = await self.mcp_client.call_tool(tool_name, {
                    "query": request.query,
                    "limit": request.limit
                })
                
                # Parse JSON response
                try:
                    data = json.loads(result["content"])
                    return {
                        "success": True,
                        "data": data,
                        "count": len(data) if isinstance(data, list) else 1
                    }
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "data": result["content"],
                        "count": 1
                    }
                    
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/ask")
        async def natural_language_query(request: NaturalLanguageRequest):
            """Process natural language query"""
            if not self.llm_client:
                raise HTTPException(
                    status_code=501, 
                    detail="Natural language processing not configured"
                )
            
            try:
                # Get schema for context
                schema_uri = f"{request.data_source}://schema" if request.data_source else "database://schema"
                schema_resource = await self.mcp_client.read_resource(schema_uri)
                schema_data = json.loads(schema_resource["content"])
                
                # Generate SQL using LLM
                sql = await self._generate_sql_from_nl(
                    request.question, 
                    schema_data, 
                    request.data_source
                )
                
                if not sql:
                    raise HTTPException(
                        status_code=400, 
                        detail="Could not generate SQL from your question"
                    )
                
                # Execute the generated SQL
                tool_name = f"query_{request.data_source}" if request.data_source else "query_mysql"
                result = await self.mcp_client.call_tool(tool_name, {
                    "query": sql,
                    "limit": request.limit
                })
                
                data = json.loads(result["content"])
                return {
                    "success": True,
                    "question": request.question,
                    "generated_sql": sql,
                    "data": data,
                    "count": len(data) if isinstance(data, list) else 1
                }
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/schema")
        async def get_schema(request: SchemaRequest = Depends()):
            """Get schema information"""
            try:
                schema_uri = f"{request.data_source}://schema" if request.data_source else "database://schema"
                schema_resource = await self.mcp_client.read_resource(schema_uri)
                schema_data = json.loads(schema_resource["content"])
                
                return {
                    "success": True,
                    "data_source": request.data_source or "default",
                    "schema": schema_data
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/refresh-schema")
        async def refresh_schema(request: SchemaRequest = Depends()):
            """Refresh schema for a data source"""
            try:
                tool_name = "refresh_schema"
                result = await self.mcp_client.call_tool(tool_name, {
                    "data_source": request.data_source or ""
                })
                
                return {
                    "success": True,
                    "message": "Schema refreshed successfully",
                    "result": json.loads(result["content"])
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/data-sources")
        async def list_data_sources():
            """List all available data sources"""
            try:
                result = await self.mcp_client.call_tool("list_data_sources", {})
                data_sources = json.loads(result["content"])
                
                return {
                    "success": True,
                    "data_sources": data_sources
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _generate_sql_from_nl(
        self, 
        question: str, 
        schema_data: Dict[str, Any], 
        data_source: Optional[str] = None
    ) -> Optional[str]:
        """Generate SQL from natural language using LLM"""
        if not self.llm_client:
            return None
        
        # Build prompt with schema context
        schema_text = json.dumps(schema_data, indent=2)[:10000]  # Limit schema size
        
        prompt = f"""
        You are a SQL assistant. Generate a single MySQL SELECT query for the user's question.
        Use ONLY tables/columns that exist in the schema. Return only the SQL query, no explanations.
        
        Schema:
        {schema_text}
        
        User question: {question}
        
        Return only the SQL starting with SELECT and ending with a semicolon.
        """
        
        try:
            response = self.llm_client.invoke(prompt)
            
            # Extract SQL from response
            sql_upper = response.upper()
            start = sql_upper.find("SELECT")
            if start == -1:
                return None
            
            end = response.find(";")
            sql = response[start:(end + 1 if end != -1 else None)].strip()
            
            return sql if sql else None
            
        except Exception as e:
            self.logger.error(f"Error generating SQL: {e}")
            return None
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a generic request"""
        request_type = request.get("type", "query")
        
        if request_type == "query":
            return await self.execute_query(QueryRequest(**request))
        elif request_type == "ask":
            return await self.natural_language_query(NaturalLanguageRequest(**request))
        elif request_type == "schema":
            return await self.get_schema(SchemaRequest(**request))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown request type: {request_type}")
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance"""
        return self.app
