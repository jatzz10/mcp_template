#!/usr/bin/env python3
"""
FileSystem MCP Server

A complete, production-ready MCP server that provides access to file systems.

Features:
- Directory traversal with depth limits
- File content reading
- File search functionality
- Security validation and path restrictions
- Static data resources (file system structure)
- Health monitoring
- Configurable via environment variables

Usage:
    python mcp_server.py

Environment Variables:
    FILESYSTEM_ROOT_PATH=/path/to/directory
    FILESYSTEM_MAX_DEPTH=5
    FILESYSTEM_INCLUDE_HIDDEN=false
    FILESYSTEM_MAX_FILE_SIZE=1048576
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime
import mimetypes

from fastmcp import FastMCP
from cachetools import TTLCache


class FileSystemMCPServer:
    """
    FileSystem MCP Server implementation.
    
    This server provides:
    - File system structure as MCP resource (structure://filesystem)
    - File system query tool (query_filesystem)
    - Structure refresh tool (refresh_structure)
    - Health monitoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_config()
        self.mcp = FastMCP(name=self.config.get('server_name', 'filesystem-mcp-server'))
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute cache
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.get('log_level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("filesystem_mcp_server")
        
        # Register MCP tools and resources
        self._register_tools()
        self._register_resources()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'server_name': os.getenv('SERVER_NAME', 'filesystem-mcp-server'),
            'server_host': os.getenv('SERVER_HOST', '127.0.0.1'),
            'server_port': int(os.getenv('SERVER_PORT', '8000')),
            'root_path': os.getenv('FILESYSTEM_ROOT_PATH', '/tmp'),
            'max_depth': int(os.getenv('FILESYSTEM_MAX_DEPTH', '5')),
            'include_hidden': os.getenv('FILESYSTEM_INCLUDE_HIDDEN', 'false').lower() == 'true',
            'include_file_content': os.getenv('FILESYSTEM_INCLUDE_FILE_CONTENT', 'false').lower() == 'true',
            'max_file_size': int(os.getenv('FILESYSTEM_MAX_FILE_SIZE', '1048576')),  # 1MB
            'allowed_extensions': os.getenv('FILESYSTEM_ALLOWED_EXTENSIONS', '').split(',') if os.getenv('FILESYSTEM_ALLOWED_EXTENSIONS') else [],
            'excluded_directories': os.getenv('FILESYSTEM_EXCLUDED_DIRS', '.git,node_modules,__pycache__').split(','),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'structure_cache_ttl': int(os.getenv('STRUCTURE_CACHE_TTL', '3600')),
            'query_cache_ttl': int(os.getenv('QUERY_CACHE_TTL', '300')),
            'max_query_limit': int(os.getenv('MAX_QUERY_LIMIT', '1000'))
        }
    
    async def connect(self) -> bool:
        """Validate file system access"""
        try:
            if not os.path.exists(self.config['root_path']):
                self.logger.error(f"Root path does not exist: {self.config['root_path']}")
                return False
            
            if not os.path.isdir(self.config['root_path']):
                self.logger.error(f"Root path is not a directory: {self.config['root_path']}")
                return False
            
            # Test read access
            os.listdir(self.config['root_path'])
            
            self.logger.info(f"Connected to file system: {self.config['root_path']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to file system: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """File system doesn't need explicit disconnection"""
        self.logger.info("Disconnected from file system")
        return True
    
    async def get_structure(self) -> Dict[str, Any]:
        """Generate file system structure"""
        try:
            structure_data = {
                "filesystem_info": await self._get_filesystem_info(),
                "directory_structure": await self._get_directory_structure(),
                "file_statistics": await self._get_file_statistics(),
                "permissions": await self._get_permissions_info(),
                "file_types": await self._get_file_types()
            }
            
            return {
                "metadata": {
                    "root_path": self.config['root_path'],
                    "max_depth": self.config['max_depth'],
                    "include_hidden": self.config['include_hidden'],
                    "generated_at": datetime.utcnow().isoformat(),
                    "cache_ttl": self.config['structure_cache_ttl']
                },
                "data": structure_data
            }
            
        except Exception as e:
            self.logger.error(f"Error generating file system structure: {e}")
            raise
    
    async def _get_filesystem_info(self) -> Dict[str, Any]:
        """Get basic file system information"""
        try:
            stat = os.statvfs(self.config['root_path'])
            
            return {
                "root_path": self.config['root_path'],
                "total_space": stat.f_frsize * stat.f_blocks,
                "free_space": stat.f_frsize * stat.f_bavail,
                "used_space": stat.f_frsize * (stat.f_blocks - stat.f_bavail),
                "max_depth": self.config['max_depth'],
                "include_hidden": self.config['include_hidden']
            }
        except Exception:
            return {
                "root_path": self.config['root_path'],
                "max_depth": self.config['max_depth'],
                "include_hidden": self.config['include_hidden']
            }
    
    async def _get_directory_structure(self) -> Dict[str, Any]:
        """Get directory structure"""
        def scan_directory(path: str, current_depth: int = 0) -> Dict[str, Any]:
            if current_depth >= self.config['max_depth']:
                return {"truncated": True, "max_depth_reached": True}
            
            try:
                items = os.listdir(path)
                structure = {
                    "type": "directory",
                    "path": path,
                    "items": {},
                    "item_count": 0
                }
                
                for item in items:
                    # Skip hidden files if not included
                    if not self.config['include_hidden'] and item.startswith('.'):
                        continue
                    
                    # Skip excluded directories
                    if item in self.config['excluded_directories']:
                        continue
                    
                    item_path = os.path.join(path, item)
                    
                    try:
                        if os.path.isdir(item_path):
                            structure["items"][item] = scan_directory(item_path, current_depth + 1)
                        else:
                            structure["items"][item] = self._get_file_info(item_path)
                        
                        structure["item_count"] += 1
                    except (PermissionError, OSError):
                        continue
                
                return structure
                
            except (PermissionError, OSError):
                return {"error": "Permission denied"}
        
        return scan_directory(self.config['root_path'])
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a specific file"""
        try:
            stat = os.stat(file_path)
            
            info = {
                "type": "file",
                "path": file_path,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "permissions": oct(stat.st_mode)[-3:],
                "extension": Path(file_path).suffix.lower()
            }
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                info["mime_type"] = mime_type
            
            return info
            
        except Exception as e:
            return {
                "type": "file",
                "path": file_path,
                "error": str(e)
            }
    
    async def _get_file_statistics(self) -> Dict[str, Any]:
        """Get file system statistics"""
        stats = {
            "total_files": 0,
            "total_directories": 0,
            "total_size": 0,
            "file_size_distribution": {},
            "extension_distribution": {}
        }
        
        def collect_stats(path: str, current_depth: int = 0):
            if current_depth >= self.config['max_depth']:
                return
            
            try:
                for item in os.listdir(path):
                    if not self.config['include_hidden'] and item.startswith('.'):
                        continue
                    if item in self.config['excluded_directories']:
                        continue
                    
                    item_path = os.path.join(path, item)
                    
                    try:
                        if os.path.isdir(item_path):
                            stats["total_directories"] += 1
                            collect_stats(item_path, current_depth + 1)
                        else:
                            stats["total_files"] += 1
                            
                            # Get file size
                            file_size = os.path.getsize(item_path)
                            stats["total_size"] += file_size
                            
                            # Size distribution
                            if file_size < 1024:
                                size_range = "< 1KB"
                            elif file_size < 1024 * 1024:
                                size_range = "1KB - 1MB"
                            elif file_size < 1024 * 1024 * 1024:
                                size_range = "1MB - 1GB"
                            else:
                                size_range = "> 1GB"
                            
                            stats["file_size_distribution"][size_range] = \
                                stats["file_size_distribution"].get(size_range, 0) + 1
                            
                            # Extension distribution
                            ext = Path(item_path).suffix.lower()
                            if ext:
                                stats["extension_distribution"][ext] = \
                                    stats["extension_distribution"].get(ext, 0) + 1
                            else:
                                stats["extension_distribution"]["no_extension"] = \
                                    stats["extension_distribution"].get("no_extension", 0) + 1
                                    
                    except (PermissionError, OSError):
                        continue
                        
            except (PermissionError, OSError):
                pass
        
        collect_stats(self.config['root_path'])
        return stats
    
    async def _get_permissions_info(self) -> Dict[str, Any]:
        """Get permissions information"""
        permissions = {
            "readable_directories": 0,
            "writable_directories": 0,
            "executable_directories": 0,
            "permission_errors": 0
        }
        
        def check_permissions(path: str, current_depth: int = 0):
            if current_depth >= self.config['max_depth']:
                return
            
            try:
                # Check directory permissions
                if os.path.isdir(path):
                    if os.access(path, os.R_OK):
                        permissions["readable_directories"] += 1
                    if os.access(path, os.W_OK):
                        permissions["writable_directories"] += 1
                    if os.access(path, os.X_OK):
                        permissions["executable_directories"] += 1
                
                # Recursively check subdirectories
                for item in os.listdir(path):
                    if not self.config['include_hidden'] and item.startswith('.'):
                        continue
                    if item in self.config['excluded_directories']:
                        continue
                    
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        check_permissions(item_path, current_depth + 1)
                        
            except (PermissionError, OSError):
                permissions["permission_errors"] += 1
        
        check_permissions(self.config['root_path'])
        return permissions
    
    async def _get_file_types(self) -> Dict[str, Any]:
        """Get file type information"""
        file_types = {
            "text_files": 0,
            "image_files": 0,
            "video_files": 0,
            "audio_files": 0,
            "archive_files": 0,
            "code_files": 0,
            "document_files": 0,
            "other_files": 0
        }
        
        # File type mappings
        text_extensions = {'.txt', '.md', '.log', '.csv', '.json', '.xml', '.yaml', '.yml'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
        archive_extensions = {'.zip', '.tar', '.gz', '.rar', '.7z', '.bz2'}
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.php', '.rb', '.go', '.rs'}
        document_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
        
        def categorize_files(path: str, current_depth: int = 0):
            if current_depth >= self.config['max_depth']:
                return
            
            try:
                for item in os.listdir(path):
                    if not self.config['include_hidden'] and item.startswith('.'):
                        continue
                    if item in self.config['excluded_directories']:
                        continue
                    
                    item_path = os.path.join(path, item)
                    
                    try:
                        if os.path.isdir(item_path):
                            categorize_files(item_path, current_depth + 1)
                        else:
                            ext = Path(item_path).suffix.lower()
                            
                            if ext in text_extensions:
                                file_types["text_files"] += 1
                            elif ext in image_extensions:
                                file_types["image_files"] += 1
                            elif ext in video_extensions:
                                file_types["video_files"] += 1
                            elif ext in audio_extensions:
                                file_types["audio_files"] += 1
                            elif ext in archive_extensions:
                                file_types["archive_files"] += 1
                            elif ext in code_extensions:
                                file_types["code_files"] += 1
                            elif ext in document_extensions:
                                file_types["document_files"] += 1
                            else:
                                file_types["other_files"] += 1
                                
                    except (PermissionError, OSError):
                        continue
                        
            except (PermissionError, OSError):
                pass
        
        categorize_files(self.config['root_path'])
        return file_types
    
    async def execute_query(self, query_type: str, path: str = "", search_term: str = "", extension: str = "", limit: int = 100) -> list:
        """Execute file system query"""
        if not await self.connect():
            raise Exception("Failed to connect to file system")
        
        try:
            if query_type == 'list':
                return await self._list_directory(path or self.config['root_path'], limit)
            elif query_type == 'search':
                return await self._search_files(search_term, extension, path or self.config['root_path'], limit)
            elif query_type == 'read':
                return await self._read_file(path, limit)
            elif query_type == 'info':
                return await self._get_file_info(path)
            else:
                raise ValueError(f"Unknown query type: {query_type}")
                
        except Exception as e:
            self.logger.error(f"File system query error: {e}")
            raise
    
    async def _list_directory(self, path: str, limit: int) -> list:
        """List directory contents"""
        try:
            if not os.path.exists(path):
                return [{"error": f"Path does not exist: {path}"}]
            
            if not os.path.isdir(path):
                return [{"error": f"Path is not a directory: {path}"}]
            
            items = []
            for item in os.listdir(path):
                if len(items) >= limit:
                    break
                
                # Skip hidden files if not included
                if not self.config['include_hidden'] and item.startswith('.'):
                    continue
                
                # Skip excluded directories
                if item in self.config['excluded_directories']:
                    continue
                
                item_path = os.path.join(path, item)
                item_info = self._get_file_info(item_path)
                items.append(item_info)
            
            return items
            
        except Exception as e:
            return [{"error": str(e)}]
    
    async def _search_files(self, search_term: str, extension: str, search_path: str, limit: int) -> list:
        """Search for files"""
        if not search_term and not extension:
            return [{"error": "Either search_term or extension must be provided"}]
        
        try:
            results = []
            for root, dirs, files in os.walk(search_path):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in self.config['excluded_directories']]
                
                # Skip hidden directories if not included
                if not self.config['include_hidden']:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if len(results) >= limit:
                        break
                    
                    # Skip hidden files if not included
                    if not self.config['include_hidden'] and file.startswith('.'):
                        continue
                    
                    file_path = os.path.join(root, file)
                    
                    # Check extension filter
                    if extension and not file.endswith(extension):
                        continue
                    
                    # Check search term
                    if search_term and search_term.lower() not in file.lower():
                        continue
                    
                    item_info = self._get_file_info(file_path)
                    results.append(item_info)
            
            return results
            
        except Exception as e:
            return [{"error": str(e)}]
    
    async def _read_file(self, path: str, limit: int) -> list:
        """Read file content"""
        try:
            if not os.path.exists(path):
                return [{"error": f"File does not exist: {path}"}]
            
            if not os.path.isfile(path):
                return [{"error": f"Path is not a file: {path}"}]
            
            file_size = os.path.getsize(path)
            if file_size > self.config['max_file_size']:
                return [{"error": f"File too large: {file_size} bytes (max: {self.config['max_file_size']})"}]
            
            # Read file content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Limit content if requested
            if limit > 0 and len(content) > limit:
                content = content[:limit] + "... (truncated)"
            
            return [{
                "path": path,
                "content": content,
                "size": file_size,
                "encoding": "utf-8"
            }]
            
        except Exception as e:
            return [{"error": str(e)}]
    
    async def validate_query(self, query_type: str, path: str, limit: int) -> bool:
        """Validate file system query parameters"""
        # Validate query type
        if query_type not in ['list', 'search', 'read', 'info']:
            return False
        
        # Validate path
        if not path and query_type in ['read', 'info']:
            return False
        
        # Prevent directory traversal
        if path and ('..' in path or not path.startswith(self.config['root_path'])):
            return False
        
        # Check limit
        if limit > self.config['max_query_limit']:
            return False
        
        # For read operations, check file size
        if query_type == 'read' and path:
            try:
                if os.path.exists(path) and os.path.isfile(path):
                    file_size = os.path.getsize(path)
                    if file_size > self.config['max_file_size']:
                        return False
            except Exception:
                return False
        
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform file system health check"""
        try:
            if not await self.connect():
                return {
                    "status": "unhealthy",
                    "root_path": self.config['root_path'],
                    "error": "Failed to connect to file system",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Test basic operations
            test_path = self.config['root_path']
            if not os.path.exists(test_path):
                return {
                    "status": "unhealthy",
                    "root_path": test_path,
                    "error": f"Root path does not exist: {test_path}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Test read access
            try:
                os.listdir(test_path)
                read_access = True
            except PermissionError:
                read_access = False
            
            return {
                "status": "healthy" if read_access else "unhealthy",
                "root_path": self.config['root_path'],
                "read_access": read_access,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "root_path": self.config['root_path'],
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _register_tools(self) -> None:
        """Register MCP tools"""
        
        @self.mcp.tool()
        async def query_filesystem(query_type: str, path: str = "", search_term: str = "", extension: str = "", limit: int = 100) -> str:
            """Execute file system query"""
            try:
                # Check cache
                cache_key = f"fs:{query_type}:{path}:{search_term}:{extension}:{limit}"
                if cache_key in self.cache:
                    return self.cache[cache_key]
                
                # Execute query
                results = await self.execute_query(query_type, path, search_term, extension, limit)
                
                # Cache result
                result_json = json.dumps(results, indent=2)
                self.cache[cache_key] = result_json
                
                return result_json
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def refresh_structure() -> str:
            """Refresh file system structure cache"""
            try:
                structure = await self.get_structure()
                return json.dumps({
                    "status": "success",
                    "generated_at": structure["metadata"]["generated_at"],
                    "root_path": structure["metadata"]["root_path"]
                })
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def health_check() -> str:
            """Check file system health"""
            health = await self.health_check()
            return json.dumps(health, indent=2)
    
    def _register_resources(self) -> None:
        """Register MCP resources"""
        
        @self.mcp.resource("structure://filesystem")
        async def filesystem_structure():
            """Get file system structure"""
            try:
                structure = await self.get_structure()
                return json.dumps(structure, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.resource("server://info")
        async def server_info():
            """Get server information"""
            return json.dumps({
                "name": self.config['server_name'],
                "root_path": self.config['root_path'],
                "version": "1.0.0",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        @self.mcp.resource("prompts://filesystem")
        async def filesystem_prompts():
            """Get filesystem-specific prompting templates and rules
            
            This resource provides LLM prompting templates specifically designed for filesystem operations.
            Includes action schemas, safety constraints, and filesystem-specific guidance.
            """
            try:
                prompts = {
                    "action_schema": self.build_action_schema_prompt(),
                    "domain_rules": self.build_domain_prompt({}),
                    "fallback_prompt": self.build_fallback_prompt(),
                    "examples": [
                        {
                            "question": "List files in the current directory",
                            "expected_action": {
                                "action": "call_tool",
                                "tool": "query_filesystem",
                                "args": {
                                    "query_type": "list",
                                    "path": "",
                                    "limit": 50
                                }
                            }
                        },
                        {
                            "question": "Search for Python files",
                            "expected_action": {
                                "action": "call_tool",
                                "tool": "query_filesystem",
                                "args": {
                                    "query_type": "search",
                                    "search_term": "",
                                    "extension": ".py",
                                    "limit": 20
                                }
                            }
                        },
                        {
                            "question": "What is the filesystem structure?",
                            "expected_action": {
                                "action": "read_resource",
                                "uri": "structure://filesystem"
                            }
                        }
                    ]
                }
                return json.dumps(prompts, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    # Prompting Methods for LLM Integration
    def build_tool_prompt(self, question: str, tools_meta: Dict[str, Any], resource_meta: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Create a comprehensive tool-aware prompt for filesystem operations
        
        Args:
            question: User's question about the filesystem
            tools_meta: Available tools metadata
            resource_meta: Available resources metadata  
            context: Additional context (structure, etc.)
        
        Returns:
            Formatted prompt string for LLM
        """
        context = context or {}
        structure_text = context.get('structure_text', '')
        
        return (
            "You are a filesystem assistant that can explore file systems and access structure information via MCP.\n\n"
            
            "AVAILABLE TOOLS:\n" +
            "\n".join([f"- {t['name']}: {t['description']}" for t in tools_meta.get("tools", [])]) + "\n\n" +
            
            "AVAILABLE RESOURCES:\n" +
            "\n".join([f"- {r['uri']}: {r['description']}" for r in resource_meta.get("resources", [])]) + "\n\n" +
            
            "FILESYSTEM STRUCTURE:\n" + (structure_text[:15000] if structure_text else "Structure not available") + "\n\n" +
            
            "USER QUESTION: " + question + "\n\n" +
            
            "RULES:\n"
            "- Only read operations are allowed. No file creation, modification, or deletion.\n"
            "- When querying the filesystem, call tool 'query_filesystem' with appropriate parameters.\n"
            "- If the user asks about structure/overview, read resource 'structure://filesystem'.\n"
            "- Always use proper file paths and respect filesystem constraints.\n"
            "- Limit results appropriately using the limit parameter.\n"
            "- Use appropriate query types: list, search, read, info.\n\n" +
            
            "OUTPUT FORMAT:\n"
            "You must respond with a single-line minified JSON object with this exact structure:\n"
            "{\"action\": \"call_tool|read_resource\", \"tool\": \"tool_name\", \"args\": {...}}\n"
            "or {\"action\": \"read_resource\", \"uri\": \"resource_uri\"}\n\n" +
            
            "EXAMPLES:\n"
            "Question: 'List files in the current directory'\n"
            "Response: {\"action\": \"call_tool\", \"tool\": \"query_filesystem\", \"args\": {\"query_type\": \"list\", \"path\": \"\", \"limit\": 50}}\n\n"
            "Question: 'Search for Python files'\n"
            "Response: {\"action\": \"call_tool\", \"tool\": \"query_filesystem\", \"args\": {\"query_type\": \"search\", \"search_term\": \"\", \"extension\": \".py\", \"limit\": 20}}\n\n"
            "Question: 'What is the filesystem structure?'\n"
            "Response: {\"action\": \"read_resource\", \"uri\": \"structure://filesystem\"}\n\n" +
            
            "IMPORTANT: Return ONLY the JSON object. No explanations, no markdown, no additional text."
        )
    
    def build_action_schema_prompt(self) -> str:
        """Get the strict JSON action schema for filesystem operations"""
        return (
            "You must respond with a single-line minified JSON object with this exact structure:\n\n"
            "For tool calls:\n"
            "{\"action\": \"call_tool\", \"tool\": \"query_filesystem\", \"args\": {\"query_type\": \"list|search|read|info\", \"path\": \"path\", \"search_term\": \"term\", \"extension\": \".ext\", \"limit\": 100}}\n\n"
            "For resource access:\n"
            "{\"action\": \"read_resource\", \"uri\": \"structure://filesystem\"}\n\n"
            "Valid tools: query_filesystem, refresh_structure, health_check\n"
            "Valid resources: structure://filesystem, server://info, prompts://filesystem\n"
            "Valid query types: list, search, read, info. Only read operations allowed."
        )
    
    def build_domain_prompt(self, context: Dict[str, Any] = None) -> str:
        """Get filesystem-specific domain rules and guidance"""
        context = context or {}
        root_path = self.config.get('root_path', '/')
        include_hidden = self.config.get('include_hidden', False)
        
        return (
            f"Filesystem Domain Rules for {root_path}:\n\n"
            
            "SAFETY CONSTRAINTS:\n"
            "- Only read operations are allowed\n"
            "- No file creation, modification, or deletion\n"
            "- No directory creation or removal\n"
            "- No permission changes\n"
            "- No symbolic link creation\n"
            "- Respect excluded directories and file types\n\n"
            
            "QUERY TYPE GUIDELINES:\n"
            "- list: List directory contents (files and subdirectories)\n"
            "- search: Search for files by name pattern or extension\n"
            "- read: Read file content (text files only)\n"
            "- info: Get detailed file/directory information\n\n"
            
            "PATH HANDLING:\n"
            "- Use absolute paths or paths relative to root\n"
            "- Paths are case-sensitive on most systems\n"
            "- Use forward slashes (/) as path separators\n"
            "- Empty path (\"\") means root directory\n"
            "- Handle special characters in filenames properly\n\n"
            
            "SEARCH PATTERNS:\n"
            "- search_term: Text to search for in filenames\n"
            "- extension: File extension filter (e.g., '.py', '.txt')\n"
            "- Use empty search_term for extension-only searches\n"
            "- Case-sensitive search by default\n\n"
            
            f"CONFIGURATION:\n"
            f"- Root path: {root_path}\n"
            f"- Include hidden files: {include_hidden}\n"
            f"- Excluded directories: {', '.join(self.config.get('excluded_directories', []))}\n"
            f"- Max file size: {self.config.get('max_file_size', 1048576)} bytes\n\n"
            
            "COMMON PATTERNS:\n"
            "- Directory listing: query_type='list', path='directory_path'\n"
            "- File search: query_type='search', search_term='filename', extension='.ext'\n"
            "- File reading: query_type='read', path='file_path'\n"
            "- File info: query_type='info', path='file_path'\n\n"
            
            "ERROR HANDLING:\n"
            "- If path doesn't exist, suggest checking available paths\n"
            "- If file is too large, suggest using info instead of read\n"
            "- If permission denied, suggest checking file permissions\n"
            "- Always validate paths against filesystem structure"
        )
    
    def build_fallback_prompt(self) -> str:
        """Get fallback prompt for when LLM response isn't valid JSON"""
        return (
            "If the LLM response is not valid JSON or doesn't follow the action schema:\n\n"
            "1. Try to extract a file path or search term from the response\n"
            "2. If no valid path found, ask user to rephrase\n"
            "3. Suggest using /structure to check available filesystem structure\n"
            "4. Provide example filesystem queries based on available structure\n\n"
            "Common fallback patterns:\n"
            "- 'list' for directory contents\n"
            "- 'search' with extension for file type searches\n"
            "- 'info' for file/directory information\n"
            "- Use empty path for root directory operations"
        )

    async def start(self) -> None:
        """Start the MCP server"""
        self.logger.info(f"Starting FileSystem MCP Server: {self.config['server_name']}")
        
        # Connect to file system
        await self.connect()
        
        # Start server
        host = self.config['server_host']
        port = self.config['server_port']
        
        self.logger.info(f"Server ready on {host}:{port} with streamable-http transport")
        self.mcp.run(transport="streamable-http", host=host, port=port)
    
    async def stop(self) -> None:
        """Stop the MCP server"""
        self.logger.info(f"Stopping FileSystem MCP Server: {self.config['server_name']}")
        await self.disconnect()
    
    def print_server_info(self) -> None:
        """Print server information"""
        print("\n" + "="*60)
        print("🚀 FileSystem MCP Server")
        print("="*60)
        print(f"📊 Root Path: {self.config['root_path']}")
        print(f"🔗 Resource: structure://filesystem")
        print(f"🛠️  Tools: query_filesystem, refresh_structure, health_check")
        print(f"🌐 Transport: streamable-http")
        
        print(f"\n📡 Server Endpoint:")
        print(f"   http://{self.config['server_host']}:{self.config['server_port']}/mcp")
        
        print(f"\n📁 File System Access:")
        print(f"   Root Path: {self.config['root_path']}")
        print(f"   Max Depth: {self.config['max_depth']}")
        print(f"   Include Hidden: {self.config['include_hidden']}")
        print(f"   Max File Size: {self.config['max_file_size']} bytes")
        
        print(f"\n📋 Available MCP Resources:")
        print(f"   • structure://filesystem - Complete file system structure")
        
        print(f"\n🔧 Available MCP Tools:")
        print(f"   • query_filesystem - Execute file system queries")
        print(f"   • refresh_structure - Refresh structure cache")
        print(f"   • health_check - Check file system health")
        
        print(f"\n📝 Query Types:")
        print(f"   • list - List directory contents")
        print(f"   • search - Search for files")
        print(f"   • read - Read file content")
        print(f"   • info - Get file information")
        
        print("\n" + "="*60)


async def main():
    """Main entry point"""
    try:
        # Create and start server
        server = FileSystemMCPServer()
        
        # Print server information
        server.print_server_info()
        
        # Start the server
        await server.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if running with help
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0)
    
    # Run the server
    asyncio.run(main())
