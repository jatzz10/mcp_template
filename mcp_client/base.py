"""
Base MCP Client implementation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json
import logging
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp import Client


class MCPClientBase(ABC):
    """
    Base class for MCP clients.
    
    Provides common functionality for connecting to MCP servers
    and executing tools/resources.
    """
    
    def __init__(self, server_url: str, config: Optional[Dict[str, Any]] = None):
        self.server_url = server_url
        self.config = config or {}
        self.transport = None
        self.client = None
        self.connected = False
        self.logger = logging.getLogger(f"mcp_client.{self.__class__.__name__}")
    
    async def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            self.transport = StreamableHttpTransport(url=self.server_url)
            self.client = Client(self.transport)
            await self.client.__aenter__()
            self.connected = True
            self.logger.info(f"Connected to MCP server: {self.server_url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from MCP server"""
        try:
            if self.client:
                await self.client.__aexit__(None, None, None)
                self.client = None
            self.connected = False
            self.logger.info("Disconnected from MCP server")
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from MCP server: {e}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        if not self.connected:
            raise Exception("Not connected to MCP server")
        
        try:
            tools = await self.client.list_tools()
            if hasattr(tools, 'tools'):
                return [{"name": t.name, "description": t.description} for t in tools.tools]
            else:
                return [{"name": t.name, "description": t.description} for t in tools]
        except Exception as e:
            self.logger.error(f"Error listing tools: {e}")
            raise
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources"""
        if not self.connected:
            raise Exception("Not connected to MCP server")
        
        try:
            resources = await self.client.list_resources()
            if hasattr(resources, 'resources'):
                return [{"uri": r.uri, "description": r.description} for r in resources.resources]
            else:
                return [{"uri": r.uri, "description": r.description} for r in resources]
        except Exception as e:
            self.logger.error(f"Error listing resources: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.connected:
            raise Exception("Not connected to MCP server")
        
        try:
            result = await self.client.call_tool(tool_name, arguments)
            return {
                "content": result.content[0].text if hasattr(result, 'content') else str(result),
                "is_error": result.isError if hasattr(result, 'isError') else False
            }
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {e}")
            raise
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        if not self.connected:
            raise Exception("Not connected to MCP server")
        
        try:
            resource = await self.client.read_resource(uri)
            if hasattr(resource, 'contents'):
                return {
                    "content": resource.contents[0].text,
                    "mime_type": getattr(resource.contents[0], 'mimeType', 'text/plain')
                }
            else:
                return {
                    "content": resource[0].text,
                    "mime_type": getattr(resource[0], 'mimeType', 'text/plain')
                }
        except Exception as e:
            self.logger.error(f"Error reading resource {uri}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MCP server health"""
        try:
            if not self.connected:
                return {"status": "disconnected", "error": "Not connected to server"}
            
            # Try to list tools as a health check
            await self.list_tools()
            return {"status": "healthy", "server_url": self.server_url}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request using the MCP server.
        
        Default implementation - can be overridden by subclasses.
        """
        request_type = request.get("type", "query")
        
        if request_type == "query":
            tool_name = request.get("tool", "query_mysql")
            args = request.get("args", {})
            result = await self.call_tool(tool_name, args)
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": f"Unknown request type: {request_type}"}
