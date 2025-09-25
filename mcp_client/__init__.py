"""
MCP Client templates
"""

from .fastapi import MCPFastAPIClient
from .base import MCPClientBase

__all__ = [
    "MCPFastAPIClient",
    "MCPClientBase"
]
