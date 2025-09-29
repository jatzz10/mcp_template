# FileSystem MCP Server

A complete, production-ready MCP server that provides secure access to file systems with directory traversal, file search, and content reading capabilities. This server exposes file system structure and query capabilities through the Model Context Protocol (MCP), enabling LLMs to interact with file systems safely and efficiently.

## 🎯 What Does This Do?

This MCP server provides:
- **File System Structure Access**: Exposes directory hierarchy and file metadata as MCP resources
- **Secure File Operations**: Allows read-only file operations with path validation and security controls
- **File Search & Discovery**: Provides search capabilities by name, extension, and content
- **LLM Integration**: Provides prompting templates for natural language to file operation conversion
- **Security Controls**: Implements path restrictions, size limits, and extension filtering
- **FastAPI Client**: Includes a REST API client with `/ask_llm` endpoint for LLM interaction

## 🛠️ Tech Stack & Main Libraries

- **FastMCP**: Modern Python SDK for MCP server/client communication
- **Streamable-HTTP Transport**: Efficient bidirectional HTTP transport for MCP
- **NailLLMLangchain**: LLM integration for natural language processing
- **Python os/pathlib**: File system operations and path handling
- **FastAPI**: Web framework for the REST API client
- **CacheTools**: In-memory caching for file system queries
- **Python-dotenv**: Environment variable management

## 🚀 Quick Start

### 1. Copy Template

```bash
cp -r templates/filesystem-mcp-server/ my-filesystem-server/
cd my-filesystem-server/
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit with your file system path
nano .env
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Server

```bash
python mcp_server.py
```

### 5. Run Client (Optional)

```bash
# In a new terminal
export MCP_SERVER_URL=http://127.0.0.1:8000/mcp
uvicorn mcp_client:app --host 0.0.0.0 --port 8001
```

### 6. Test the Setup

```bash
# Test server health
curl http://127.0.0.1:8000/health

# Test client health
curl http://127.0.0.1:8001/health

# Test LLM integration (requires NAIL_LLM_API_KEY)
curl -X POST http://127.0.0.1:8001/ask_llm \
  -H "Content-Type: application/json" \
  -d '{"question": "List all Python files in the project"}'
```

## 🔧 Configuration

### Environment Variables

```bash
# Server Configuration
SERVER_NAME=filesystem-mcp-server
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# FileSystem Configuration
FILESYSTEM_ROOT_PATH=/path/to/directory    # Root directory path
FILESYSTEM_MAX_DEPTH=5                     # Maximum directory depth
FILESYSTEM_INCLUDE_HIDDEN=false            # Include hidden files/directories
FILESYSTEM_INCLUDE_FILE_CONTENT=false      # Include file content in structure
FILESYSTEM_MAX_FILE_SIZE=1048576           # Maximum file size to read (1MB)
FILESYSTEM_ALLOWED_EXTENSIONS=             # Comma-separated allowed extensions
FILESYSTEM_EXCLUDED_DIRS=.git,node_modules,__pycache__  # Excluded directories

# Cache Configuration
STRUCTURE_CACHE_TTL=3600                   # Structure cache TTL (1 hour)
QUERY_CACHE_TTL=300                        # Query cache TTL (5 minutes)
MAX_QUERY_LIMIT=1000                       # Maximum query results
```

### Security Configuration

#### Path Restrictions
```bash
# Restrict to specific directory
FILESYSTEM_ROOT_PATH=/var/www/html

# Limit directory depth
FILESYSTEM_MAX_DEPTH=3

# Exclude sensitive directories
FILESYSTEM_EXCLUDED_DIRS=.git,node_modules,__pycache__,venv,env
```

#### File Type Filtering
```bash
# Allow only specific file types
FILESYSTEM_ALLOWED_EXTENSIONS=.txt,.md,.json,.yaml,.py,.js

# Limit file size
FILESYSTEM_MAX_FILE_SIZE=524288  # 512KB
```

#### Hidden Files
```bash
# Include hidden files (use with caution)
FILESYSTEM_INCLUDE_HIDDEN=true

# Exclude hidden files (recommended)
FILESYSTEM_INCLUDE_HIDDEN=false
```

## 📋 MCP Resources

- **`structure://filesystem`** - Complete file system structure including:
  - Directory hierarchy with depth limits
  - File metadata (size, type, permissions)
  - File type categorization
  - Permission information
  - File system statistics

- **`prompts://filesystem`** - LLM prompting templates including:
  - Action schemas for tool/resource selection
  - File system-specific rules and constraints
  - Example file operations and expected responses
  - Safety guidelines for file system operations

## 🔧 MCP Tools

- **`query_filesystem`** - Execute file system queries with:
  - **list** - List directory contents
  - **search** - Search for files by name or extension
  - **read** - Read file content
  - **info** - Get file/directory information

- **`refresh_structure`** - Refresh structure cache
- **`health_check`** - Check file system health

## 🧪 Testing

### Test Server

```bash
# Test file system access
python test_filesystem.py

# Test MCP client
python mcp_client.py
```

### Example Queries

```python
# List directory contents
result = await client.call_tool("query_filesystem", {
    "query_type": "list",
    "path": "/path/to/directory",
    "limit": 50
})

# Search for Python files
result = await client.call_tool("query_filesystem", {
    "query_type": "search",
    "search_term": "",
    "extension": ".py",
    "limit": 100
})

# Search for files by name
result = await client.call_tool("query_filesystem", {
    "query_type": "search",
    "search_term": "config",
    "limit": 50
})

# Read file content
result = await client.call_tool("query_filesystem", {
    "query_type": "read",
    "path": "/path/to/file.txt",
    "limit": 1
})

# Get file information
result = await client.call_tool("query_filesystem", {
    "query_type": "info",
    "path": "/path/to/file.txt",
    "limit": 1
})
```

## 🔒 Security Features

### Path Validation

- **Root path restriction** - All access limited to configured root path
- **Directory traversal protection** - Blocks `../` and `//` patterns
- **Depth limiting** - Prevents deep directory traversal
- **Excluded directories** - Blocks access to sensitive directories

### File Access Control

- **File size limits** - Prevents reading large files
- **Extension filtering** - Restricts file types
- **Permission checking** - Validates read access
- **Hidden file control** - Configurable hidden file access

### Security Examples

```bash
# Secure configuration for web content
FILESYSTEM_ROOT_PATH=/var/www/html
FILESYSTEM_MAX_DEPTH=3
FILESYSTEM_INCLUDE_HIDDEN=false
FILESYSTEM_ALLOWED_EXTENSIONS=.html,.css,.js,.json,.txt
FILESYSTEM_EXCLUDED_DIRS=.git,node_modules,logs,tmp

# Development configuration
FILESYSTEM_ROOT_PATH=/home/user/projects
FILESYSTEM_MAX_DEPTH=5
FILESYSTEM_INCLUDE_HIDDEN=true
FILESYSTEM_MAX_FILE_SIZE=2097152  # 2MB
```

## 📈 Performance

### Caching Strategy

- **Structure caching**: File-based with 1-hour TTL
- **Query caching**: Memory-based with 5-minute TTL
- **Automatic refresh**: When structure becomes stale
- **Manual refresh**: Via `refresh_structure` tool

### Query Optimization

- **Depth limiting**: Prevents excessive directory traversal
- **Result limiting**: Maximum 1000 results per query
- **File size limits**: Prevents memory issues
- **Extension filtering**: Reduces search scope

## 🐛 Troubleshooting

### Common Issues

1. **Permission Denied**
   ```
   Error: Permission denied
   ```
   - Check file system permissions
   - Verify user has read access
   - Check SELinux/AppArmor policies

2. **Path Not Found**
   ```
   Error: Path does not exist
   ```
   - Verify root path exists
   - Check path configuration
   - Ensure directory is accessible

3. **File Too Large**
   ```
   Error: File too large
   ```
   - Increase `FILESYSTEM_MAX_FILE_SIZE`
   - Use file filtering
   - Consider file chunking

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python mcp_server.py
```

### Health Check

```python
# Check file system health
health = await client.call_tool("health_check")
print(health)
```

## 🔄 Structure Refresh

### Automatic Refresh

The structure is automatically refreshed when:
- Cache file doesn't exist
- Cache is older than TTL (1 hour)
- Structure changes detected

### Manual Refresh

```python
# Refresh structure cache
result = await client.call_tool("refresh_structure")
print(result)
```

## 📚 Advanced Usage

### Custom Configuration

```python
# Custom server configuration
config = {
    'server_name': 'my-fs-server',
    'root_path': '/custom/path',
    'max_depth': 10,
    'include_hidden': True,
    'max_file_size': 5242880,  # 5MB
    'allowed_extensions': ['.py', '.js', '.md'],
    'excluded_directories': ['.git', 'node_modules']
}

server = FileSystemMCPServer(config)
await server.start()
```

### Multiple File Systems

```python
# Support multiple file system roots
class MultiFileSystemServer:
    def __init__(self):
        self.servers = {}
    
    def add_filesystem(self, name, config):
        self.servers[name] = FileSystemMCPServer(config)
```

## 🎯 Best Practices

1. **Use restrictive root paths** for security
2. **Set appropriate depth limits** to prevent traversal
3. **Exclude sensitive directories** like `.git`, `node_modules`
4. **Limit file sizes** to prevent memory issues
5. **Use extension filtering** for specific file types
6. **Monitor file system access** and log suspicious activity
7. **Regular security audits** of file system permissions
8. **Backup important data** before making changes

## 🏗️ Architecture & Implementation Details

### MCP Server Implementation

The MCP server (`mcp_server.py`) implements:

1. **File System Access Management**:
   - Root path restriction and validation
   - Directory traversal protection
   - Permission checking and validation
   - Security policy enforcement

2. **Structure Management**:
   - File-based caching with TTL (1 hour)
   - Automatic structure refresh when stale
   - Comprehensive metadata extraction
   - File type categorization

3. **Query Execution**:
   - Security validation (read-only operations)
   - Path sanitization and validation
   - File size and extension filtering
   - Result caching (5-minute TTL)

4. **LLM Integration**:
   - Server-side prompting templates
   - Action schemas for tool selection
   - File system-specific rules and examples
   - Safety constraints and guidelines

5. **MCP Protocol**:
   - FastMCP with streamable-http transport
   - Tool registration (`query_filesystem`, `refresh_structure`, `health_check`)
   - Resource registration (`structure://filesystem`, `prompts://filesystem`)

### FastAPI Client Implementation

The FastAPI client (`mcp_client.py`) provides:

1. **MCP Communication**:
   - FastMCP client with streamable-http transport
   - Tool and resource calling capabilities
   - Error handling and logging

2. **REST API Endpoints**:
   - `/query` - Direct file system query execution
   - `/structure` - Get file system structure
   - `/health` - Health check
   - `/ask_llm` - LLM-powered natural language queries

3. **LLM Integration**:
   - NailLLMLangchain integration
   - Fetches server-side prompts
   - Composes final prompts with user questions
   - Parses LLM JSON actions and executes MCP calls

4. **Request/Response Flow**:
   ```
   User Question → /ask_llm → Fetch prompts://filesystem → 
   Compose prompt → LLM invoke → Parse JSON action → 
   Execute MCP tool/resource → Return result
   ```

### Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   MCP Server     │    │   File System   │
│   Client        │◄──►│   (FastMCP)      │◄──►│   (Local/Remote)│
│   (Port 8001)   │    │   (Port 8000)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   NailLLM       │    │   Structure      │
│   Langchain     │    │   Cache          │
└─────────────────┘    └──────────────────┘
```

## 📞 Support

For issues specific to FileSystem MCP server:

1. Check the troubleshooting section above
2. Review file system permissions
3. Test file system access manually
4. Check security policies (SELinux, AppArmor)
5. Verify path configurations
6. Review template documentation
