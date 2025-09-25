"""
Abstract base class for MCP data sources
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json
from datetime import datetime


class MCPDataSource(ABC):
    """
    Abstract base class for all MCP data sources.
    
    Each data source must implement:
    - Schema generation and caching
    - Query execution
    - Connection management
    - Error handling
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.connected = False
        self.schema_cache_ttl = config.get('schema_cache_ttl', 3600)  # 1 hour default
        self.query_cache_ttl = config.get('query_cache_ttl', 300)    # 5 minutes default
        self.max_query_limit = config.get('max_query_limit', 1000)
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the data source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection to the data source"""
        pass
    
    @abstractmethod
    async def get_schema(self) -> Dict[str, Any]:
        """
        Generate and return schema information.
        
        Returns:
            Dict containing schema metadata, tables/endpoints, relationships, etc.
        """
        pass
    
    @abstractmethod
    async def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a query against the data source.
        
        Args:
            query_params: Query parameters (SQL, API params, etc.)
            
        Returns:
            List of result records
        """
        pass
    
    @abstractmethod
    async def validate_query(self, query_params: Dict[str, Any]) -> bool:
        """
        Validate query parameters for security and correctness.
        
        Args:
            query_params: Query parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def get_schema_metadata(self) -> Dict[str, Any]:
        """Get metadata about the schema"""
        return {
            "data_source": self.name,
            "generated_at": datetime.utcnow().isoformat(),
            "cache_ttl": self.schema_cache_ttl,
            "max_query_limit": self.max_query_limit,
            "config": {k: v for k, v in self.config.items() if 'password' not in k.lower()}
        }
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get MCP tool definition for this data source"""
        return {
            "name": f"query_{self.name}",
            "description": f"Execute queries against {self.name} data source",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": f"Query to execute against {self.name}"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 100,
                        "maximum": self.max_query_limit
                    }
                },
                "required": ["query"]
            }
        }
    
    def get_resource_definition(self) -> Dict[str, Any]:
        """Get MCP resource definition for this data source"""
        return {
            "uri": f"{self.name}://schema",
            "name": f"{self.name} Schema",
            "description": f"Schema information for {self.name} data source",
            "mimeType": "application/json"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the data source"""
        try:
            if not self.connected:
                await self.connect()
            
            # Try a simple query to verify connection
            test_result = await self.query({"query": "SELECT 1", "limit": 1})
            
            return {
                "status": "healthy",
                "data_source": self.name,
                "connected": self.connected,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "data_source": self.name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
