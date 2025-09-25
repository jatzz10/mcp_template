"""
Base MCP Server implementation
"""

from typing import Dict, Any, List, Optional
import json
import logging
from fastmcp import FastMCP
from .datasource import MCPDataSource
from .schema import SchemaManager
from .cache import CacheManager


class MCPServer:
    """
    Base MCP Server that can handle multiple data sources.
    
    Features:
    - Multiple data source support
    - Schema management and caching
    - Query result caching
    - Health monitoring
    - Configurable transport
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.mcp = FastMCP(name=name)
        self.data_sources: Dict[str, MCPDataSource] = {}
        self.schema_manager = SchemaManager()
        self.cache_manager = CacheManager()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"mcp_server.{name}")
        
        # Register base tools and resources
        self._register_base_tools()
        self._register_base_resources()
    
    def add_data_source(self, name: str, data_source: MCPDataSource) -> None:
        """Add a data source to the server"""
        self.data_sources[name] = data_source
        self._register_data_source_tools(name, data_source)
        self._register_data_source_resources(name, data_source)
        self.logger.info(f"Added data source: {name}")
    
    def _register_base_tools(self) -> None:
        """Register base MCP tools"""
        
        @self.mcp.tool()
        async def list_data_sources() -> str:
            """List all available data sources"""
            sources = []
            for name, ds in self.data_sources.items():
                sources.append({
                    "name": name,
                    "type": ds.__class__.__name__,
                    "connected": ds.connected,
                    "config": ds.get_schema_metadata()
                })
            return json.dumps(sources, indent=2)
        
        @self.mcp.tool()
        async def health_check() -> str:
            """Check health of all data sources"""
            health_status = {}
            for name, ds in self.data_sources.items():
                health_status[name] = await ds.health_check()
            return json.dumps(health_status, indent=2)
        
        @self.mcp.tool()
        async def refresh_schema(data_source: str = "") -> str:
            """Refresh schema for a specific data source or all sources"""
            if data_source:
                if data_source not in self.data_sources:
                    return json.dumps({"error": f"Data source '{data_source}' not found"})
                
                ds = self.data_sources[data_source]
                try:
                    schema = await ds.get_schema()
                    await self.schema_manager.save_schema(data_source, schema)
                    return json.dumps({
                        "status": "success",
                        "data_source": data_source,
                        "generated_at": schema.get("metadata", {}).get("generated_at")
                    })
                except Exception as e:
                    return json.dumps({"error": str(e)})
            else:
                # Refresh all data sources
                results = {}
                for name, ds in self.data_sources.items():
                    try:
                        schema = await ds.get_schema()
                        await self.schema_manager.save_schema(name, schema)
                        results[name] = {"status": "success"}
                    except Exception as e:
                        results[name] = {"status": "error", "error": str(e)}
                return json.dumps(results, indent=2)
    
    def _register_base_resources(self) -> None:
        """Register base MCP resources"""
        
        @self.mcp.resource("server://info")
        async def server_info():
            """Get server information and configuration"""
            return json.dumps({
                "name": self.name,
                "data_sources": list(self.data_sources.keys()),
                "config": self.config,
                "version": "1.0.0"
            })
    
    def _register_data_source_tools(self, name: str, data_source: MCPDataSource) -> None:
        """Register tools for a specific data source"""
        
        @self.mcp.tool()
        async def query_data_source(query: str, limit: int = 100) -> str:
            """Execute a query against the data source"""
            # Validate query
            if not await data_source.validate_query({"query": query, "limit": limit}):
                return json.dumps({"error": "Invalid query parameters"})
            
            # Check cache first
            cache_key = f"{name}:{hash(query)}:{limit}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.info(f"Cache hit for query: {name}")
                return cached_result
            
            try:
                # Execute query
                results = await data_source.query({"query": query, "limit": limit})
                
                # Cache result
                result_json = json.dumps(results, indent=2)
                await self.cache_manager.set(cache_key, result_json, ttl=data_source.query_cache_ttl)
                
                return result_json
            except Exception as e:
                self.logger.error(f"Query error for {name}: {e}")
                return json.dumps({"error": str(e)})
        
        # Set the tool name dynamically
        query_data_source.__name__ = f"query_{name}"
        query_data_source.__doc__ = f"Execute queries against {name} data source"
    
    def _register_data_source_resources(self, name: str, data_source: MCPDataSource) -> None:
        """Register resources for a specific data source"""
        
        @self.mcp.resource(f"{name}://schema")
        async def data_source_schema():
            """Get schema for the data source"""
            # Check if schema is cached and fresh
            cached_schema = await self.schema_manager.get_schema(name)
            if cached_schema:
                return json.dumps(cached_schema)
            
            # Generate fresh schema
            try:
                schema = await data_source.get_schema()
                await self.schema_manager.save_schema(name, schema)
                return json.dumps(schema)
            except Exception as e:
                self.logger.error(f"Schema generation error for {name}: {e}")
                return json.dumps({"error": str(e)})
    
    async def start(self) -> None:
        """Start the MCP server"""
        self.logger.info(f"Starting MCP server: {self.name}")
        
        # Connect to all data sources
        for name, ds in self.data_sources.items():
            try:
                await ds.connect()
                self.logger.info(f"Connected to data source: {name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {name}: {e}")
        
        # Start server
        transport = self.config.get("transport", "streamable-http")
        port = self.config.get("port", 8000)
        host = self.config.get("host", "127.0.0.1")
        
        self.logger.info(f"Server ready on {host}:{port} with {transport} transport")
        self.mcp.run(transport=transport, host=host, port=port)
    
    async def stop(self) -> None:
        """Stop the MCP server"""
        self.logger.info(f"Stopping MCP server: {self.name}")
        
        # Disconnect from all data sources
        for name, ds in self.data_sources.items():
            try:
                await ds.disconnect()
                self.logger.info(f"Disconnected from data source: {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return {
            "name": self.name,
            "data_sources": list(self.data_sources.keys()),
            "config": self.config,
            "status": "running"
        }
