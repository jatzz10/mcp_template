# REST API MCP Server

A complete, production-ready MCP server that connects to REST APIs with multiple authentication methods. This server exposes API endpoints and query capabilities through the Model Context Protocol (MCP), enabling LLMs to interact with REST APIs safely and efficiently.

## 🎯 What Does This Do?

This MCP server provides:
- **API Endpoint Discovery**: Automatically discovers and catalogs available API endpoints
- **Safe API Queries**: Allows read-only HTTP requests (GET, HEAD, OPTIONS) with security validation
- **Multiple Authentication**: Supports Bearer tokens, Basic auth, API keys, and no-auth APIs
- **LLM Integration**: Provides prompting templates for natural language to API call conversion
- **Rate Limiting**: Implements configurable rate limiting and retry logic
- **FastAPI Client**: Includes a REST API client with `/ask_llm` endpoint for LLM interaction

## 🛠️ Tech Stack & Main Libraries

- **FastMCP**: Modern Python SDK for MCP server/client communication
- **Streamable-HTTP Transport**: Efficient bidirectional HTTP transport for MCP
- **NailLLMLangchain**: LLM integration for natural language processing
- **HTTPX**: Async HTTP client for API requests
- **FastAPI**: Web framework for the REST API client
- **CacheTools**: In-memory caching for API responses
- **Python-dotenv**: Environment variable management

## 🚀 Quick Start

### 1. Copy Template

```bash
cp -r templates/rest-api-mcp-server/ my-api-server/
cd my-api-server/
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit with your API credentials
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
  -d '{"question": "Get all users from the API"}'
```

## 🔧 Configuration

### Environment Variables

```bash
# Server Configuration
SERVER_NAME=rest-api-mcp-server
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# API Configuration
API_BASE_URL=https://api.example.com
API_AUTH_TYPE=none                    # Options: none, bearer, basic, api_key
API_AUTH_TOKEN=your_token_here        # For bearer or api_key auth
API_USERNAME=your_username            # For basic auth
API_PASSWORD=your_password            # For basic auth

# API Settings
API_TIMEOUT=30                        # Request timeout in seconds
API_RATE_LIMIT=100                    # Requests per minute
API_RETRY_ATTEMPTS=3                  # Number of retry attempts

# Cache Configuration
ENDPOINTS_CACHE_TTL=3600              # Endpoints cache TTL (1 hour)
QUERY_CACHE_TTL=300                   # Query cache TTL (5 minutes)
MAX_QUERY_LIMIT=1000                  # Maximum query results
```

### Authentication Types

#### No Authentication
```bash
API_AUTH_TYPE=none
API_BASE_URL=https://public-api.example.com
```

#### Bearer Token
```bash
API_AUTH_TYPE=bearer
API_AUTH_TOKEN=your_bearer_token
API_BASE_URL=https://api.example.com
```

#### Basic Authentication
```bash
API_AUTH_TYPE=basic
API_USERNAME=your_username
API_PASSWORD=your_password
API_BASE_URL=https://api.example.com
```

#### API Key
```bash
API_AUTH_TYPE=api_key
API_AUTH_TOKEN=your_api_key
API_BASE_URL=https://api.example.com
```

## 📋 MCP Resources

- **`endpoints://api`** - Complete API endpoint documentation including:
  - Discovered endpoints with descriptions
  - HTTP methods and parameters
  - Sample responses
  - Authentication requirements

- **`prompts://rest-api`** - LLM prompting templates including:
  - Action schemas for tool/resource selection
  - API-specific rules and constraints
  - Example API calls and expected responses
  - Safety guidelines for API operations

## 🔧 MCP Tools

- **`query_api`** - Execute API queries with:
  - HTTP method validation (GET, HEAD, OPTIONS only)
  - Rate limiting and retry logic
  - Response caching
  - Error handling

- **`refresh_endpoints`** - Refresh endpoint cache
- **`health_check`** - Check API health

## 🧪 Testing

### Test Server

```bash
# Test API connection
python test_rest_api.py

# Test MCP client
python mcp_client.py
```

### Example Queries

```python
# Basic API query
result = await client.call_tool("query_api", {
    "endpoint": "/users",
    "method": "GET",
    "params": {"limit": 10},
    "limit": 50
})

# Health check
result = await client.call_tool("query_api", {
    "endpoint": "/health",
    "method": "GET",
    "limit": 1
})

# Search with parameters
result = await client.call_tool("query_api", {
    "endpoint": "/search",
    "method": "GET",
    "params": {"q": "search_term", "type": "user"},
    "limit": 100
})
```

## 🔒 Security Features

### Query Validation

- **Only safe HTTP methods** are allowed (GET, HEAD, OPTIONS)
- **Rate limiting** prevents API abuse
- **Retry logic** with exponential backoff
- **Timeout protection** prevents hanging requests

### Blocked Operations

```http
# These requests will be rejected:
POST /api/users          # POST operations
PUT /api/users/123       # PUT operations
DELETE /api/users/123    # DELETE operations
PATCH /api/users/123     # PATCH operations
```

## 📈 Performance

### Caching Strategy

- **Endpoint caching**: File-based with 1-hour TTL
- **Query caching**: Memory-based with 5-minute TTL
- **Automatic refresh**: When endpoints become stale
- **Manual refresh**: Via `refresh_endpoints` tool

### Rate Limiting

- **Configurable limits**: Default 100 requests per minute
- **Automatic throttling**: When limits are exceeded
- **Retry logic**: 3 attempts with exponential backoff
- **Timeout handling**: 30-second default timeout

## 🐛 Troubleshooting

### Common Issues

1. **Connection Failed**
   ```
   Error: Failed to connect to REST API
   ```
   - Check API base URL is correct
   - Verify network connectivity
   - Check authentication credentials

2. **Authentication Failed**
   ```
   Error: 401 Unauthorized
   ```
   - Verify authentication type
   - Check token/credentials
   - Ensure API key is valid

3. **Rate Limit Exceeded**
   ```
   Error: 429 Too Many Requests
   ```
   - Increase rate limit in configuration
   - Implement request throttling
   - Check API usage quotas

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python mcp_server.py
```

### Health Check

```python
# Check API health
health = await client.call_tool("health_check")
print(health)
```

## 🔄 Endpoint Discovery

### Automatic Discovery

The server automatically discovers endpoints by:

1. **Trying discovery endpoint** - `/discovery` or `/schema`
2. **Common endpoint patterns** - `/users`, `/products`, `/orders`
3. **API versioning** - `/api/v1/users`, `/api/v2/users`
4. **Health endpoints** - `/health`, `/status`, `/info`

### Manual Refresh

```python
# Refresh endpoint cache
result = await client.call_tool("refresh_endpoints")
print(result)
```

## 📚 Advanced Usage

### Custom Configuration

```python
# Custom server configuration
config = {
    'server_name': 'my-api-server',
    'api_base_url': 'https://api.example.com',
    'api_auth_type': 'bearer',
    'api_auth_token': 'your_token',
    'api_timeout': 60,
    'api_rate_limit': 200
}

server = RestAPIMCPServer(config)
await server.start()
```

### Multiple APIs

```python
# Support multiple API connections
class MultiAPIServer:
    def __init__(self):
        self.servers = {}
    
    def add_api(self, name, config):
        self.servers[name] = RestAPIMCPServer(config)
```

## 🎯 Best Practices

1. **Use appropriate authentication** for your API
2. **Set reasonable rate limits** to avoid API abuse
3. **Monitor API usage** and adjust limits as needed
4. **Cache responses** when appropriate
5. **Handle errors gracefully** in client applications
6. **Use HTTPS** for production APIs
7. **Validate responses** before processing
8. **Implement retry logic** for transient failures

## 🏗️ Architecture & Implementation Details

### MCP Server Implementation

The MCP server (`mcp_server.py`) implements:

1. **API Connection Management**:
   - Multiple authentication methods (Bearer, Basic, API Key, None)
   - HTTPX async client with connection pooling
   - Automatic retry logic with exponential backoff

2. **Endpoint Discovery**:
   - File-based caching with TTL (1 hour)
   - Automatic endpoint discovery via common patterns
   - API schema parsing and documentation

3. **Query Execution**:
   - Security validation (GET, HEAD, OPTIONS only)
   - Rate limiting and request throttling
   - Response caching (5-minute TTL)
   - Timeout protection

4. **LLM Integration**:
   - Server-side prompting templates
   - Action schemas for tool selection
   - API-specific rules and examples
   - Safety constraints and guidelines

5. **MCP Protocol**:
   - FastMCP with streamable-http transport
   - Tool registration (`query_api`, `refresh_endpoints`, `health_check`)
   - Resource registration (`endpoints://api`, `prompts://rest-api`)

### FastAPI Client Implementation

The FastAPI client (`mcp_client.py`) provides:

1. **MCP Communication**:
   - FastMCP client with streamable-http transport
   - Tool and resource calling capabilities
   - Error handling and logging

2. **REST API Endpoints**:
   - `/query` - Direct API query execution
   - `/endpoints` - Get API endpoints documentation
   - `/health` - Health check
   - `/ask_llm` - LLM-powered natural language queries

3. **LLM Integration**:
   - NailLLMLangchain integration
   - Fetches server-side prompts
   - Composes final prompts with user questions
   - Parses LLM JSON actions and executes MCP calls

4. **Request/Response Flow**:
   ```
   User Question → /ask_llm → Fetch prompts://rest-api → 
   Compose prompt → LLM invoke → Parse JSON action → 
   Execute MCP tool/resource → Return result
   ```

### Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   MCP Server     │    │   REST API      │
│   Client        │◄──►│   (FastMCP)      │◄──►│   (External)    │
│   (Port 8001)   │    │   (Port 8000)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   NailLLM       │    │   Endpoints      │
│   Langchain     │    │   Cache          │
└─────────────────┘    └──────────────────┘
```

## 📞 Support

For issues specific to REST API MCP server:

1. Check the troubleshooting section above
2. Review API server logs
3. Test API connectivity manually
4. Verify authentication credentials
5. Check API documentation
6. Review template documentation
