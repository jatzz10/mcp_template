# JIRA MCP Server

A complete, production-ready MCP server that connects to JIRA Cloud and Server instances, providing access to projects, issues, workflows, and metadata. This server exposes JIRA project information and query capabilities through the Model Context Protocol (MCP), enabling LLMs to interact with JIRA safely and efficiently.

## 🎯 What Does This Do?

This MCP server provides:
- **JIRA Project Access**: Exposes project metadata, workflows, and issue information as MCP resources
- **Safe JIRA Queries**: Allows read-only JQL queries with security validation
- **Workflow Discovery**: Automatically discovers and catalogs project workflows and transitions
- **LLM Integration**: Provides prompting templates for natural language to JQL conversion
- **Authentication**: Supports both JIRA Cloud (API tokens) and JIRA Server authentication
- **FastAPI Client**: Includes a REST API client with `/ask_llm` endpoint for LLM interaction

## 🛠️ Tech Stack & Main Libraries

- **FastMCP**: Modern Python SDK for MCP server/client communication
- **Streamable-HTTP Transport**: Efficient bidirectional HTTP transport for MCP
- **NailLLMLangchain**: LLM integration for natural language processing
- **HTTPX**: Async HTTP client for JIRA API requests
- **FastAPI**: Web framework for the REST API client
- **CacheTools**: In-memory caching for JIRA queries
- **Python-dotenv**: Environment variable management

## 🚀 Quick Start

### 1. Copy Template

```bash
cp -r templates/jira-mcp-server/ my-jira-server/
cd my-jira-server/
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit with your JIRA credentials
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
  -d '{"question": "Show me all open issues in the project"}'
```

## 🔧 Configuration

### Environment Variables

```bash
# Server Configuration
SERVER_NAME=jira-mcp-server
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# JIRA Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net  # JIRA base URL
JIRA_USERNAME=your-email@example.com             # JIRA username/email
JIRA_API_TOKEN=your-api-token                    # JIRA API token
JIRA_PROJECT_KEY=PROJ                            # JIRA project key

# JIRA Settings
JIRA_TIMEOUT=30                                  # Request timeout in seconds

# Cache Configuration
WORKFLOWS_CACHE_TTL=3600                         # Workflows cache TTL (1 hour)
QUERY_CACHE_TTL=300                              # Query cache TTL (5 minutes)
MAX_QUERY_LIMIT=1000                             # Maximum query results
```

### JIRA Cloud Setup

#### 1. Get API Token
1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a label (e.g., "MCP Server")
4. Copy the generated token

#### 2. Configure Environment
```bash
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJ
```

### JIRA Server Setup

#### 1. Get API Token
1. Go to JIRA → Profile → Personal Access Tokens
2. Create a new token
3. Copy the generated token

#### 2. Configure Environment
```bash
JIRA_BASE_URL=https://your-jira-server.com
JIRA_USERNAME=your-username
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJ
```

## 📋 MCP Resources

- **`workflows://jira`** - Complete JIRA project metadata including:
  - Project information and components
  - Issue types and custom fields
  - Workflow schemes and transitions
  - User permissions and roles
  - Version and release information

- **`prompts://jira`** - LLM prompting templates including:
  - Action schemas for tool/resource selection
  - JIRA-specific rules and constraints
  - Example JQL queries and expected responses
  - Safety guidelines for JIRA operations

## 🔧 MCP Tools

- **`query_jira`** - Execute JIRA queries with:
  - **search** - Search issues using JQL
  - **issue** - Get specific issue details
  - **components** - Get project components
  - **versions** - Get project versions

- **`refresh_workflows`** - Refresh workflows cache
- **`health_check`** - Check JIRA health

## 🧪 Testing

### Test Server

```bash
# Test JIRA connection
python test_jira.py

# Test MCP client
python mcp_client.py
```

### Example Queries

```python
# Search for all project issues
result = await client.call_tool("query_jira", {
    "query_type": "search",
    "jql": 'project = "PROJ" ORDER BY created DESC',
    "limit": 50
})

# Search for open issues
result = await client.call_tool("query_jira", {
    "query_type": "search",
    "jql": 'project = "PROJ" AND status = "Open"',
    "limit": 100
})

# Get specific issue
result = await client.call_tool("query_jira", {
    "query_type": "issue",
    "issue_key": "PROJ-123",
    "limit": 1
})

# Get project components
result = await client.call_tool("query_jira", {
    "query_type": "components",
    "limit": 50
})

# Get project versions
result = await client.call_tool("query_jira", {
    "query_type": "versions",
    "limit": 50
})
```

## 🔒 Security Features

### Query Validation

- **JQL validation** - Only safe JQL queries allowed
- **Dangerous operation blocking** - Blocks DELETE, UPDATE, CREATE operations
- **Query limits** - Maximum 1000 results per query
- **Authentication required** - All operations require valid credentials

### Blocked Operations

```jql
-- These JQL queries will be rejected:
DELETE FROM issues                    -- DELETE operations
UPDATE issues SET status = "Done"    -- UPDATE operations
CREATE issue                         -- CREATE operations
```

## 📈 Performance

### Caching Strategy

- **Workflows caching**: File-based with 1-hour TTL
- **Query caching**: Memory-based with 5-minute TTL
- **Automatic refresh**: When workflows become stale
- **Manual refresh**: Via `refresh_workflows` tool

### Query Optimization

- **Result limiting**: Maximum 1000 results per query
- **Connection pooling**: Reused JIRA connections
- **Error handling**: Graceful degradation
- **Timeout protection**: 30-second default timeout

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```
   Error: 401 Unauthorized
   ```
   - Check JIRA username and API token
   - Verify API token is valid and not expired
   - Ensure user has project access

2. **Project Not Found**
   ```
   Error: Project 'PROJ' not found
   ```
   - Verify project key is correct
   - Check user has access to the project
   - Ensure project exists and is active

3. **Permission Denied**
   ```
   Error: 403 Forbidden
   ```
   - Check user permissions in JIRA
   - Verify project access rights
   - Contact JIRA administrator

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python mcp_server.py
```

### Health Check

```python
# Check JIRA health
health = await client.call_tool("health_check")
print(health)
```

## 🔄 Workflows Refresh

### Automatic Refresh

The workflows are automatically refreshed when:
- Cache file doesn't exist
- Cache is older than TTL (1 hour)
- Workflow changes detected

### Manual Refresh

```python
# Refresh workflows cache
result = await client.call_tool("refresh_workflows")
print(result)
```

## 📚 Advanced Usage

### Custom Configuration

```python
# Custom server configuration
config = {
    'server_name': 'my-jira-server',
    'jira_base_url': 'https://my-domain.atlassian.net',
    'jira_username': 'user@example.com',
    'jira_api_token': 'your-token',
    'jira_project_key': 'PROJ',
    'jira_timeout': 60
}

server = JiraMCPServer(config)
await server.start()
```

### Multiple Projects

```python
# Support multiple JIRA projects
class MultiProjectJiraServer:
    def __init__(self):
        self.servers = {}
    
    def add_project(self, name, config):
        self.servers[name] = JiraMCPServer(config)
```

## 🎯 Best Practices

1. **Use API tokens** instead of passwords
2. **Limit project access** to necessary projects only
3. **Set appropriate query limits** to prevent large result sets
4. **Monitor API usage** and respect rate limits
5. **Cache frequently accessed data** to reduce API calls
6. **Handle errors gracefully** in client applications
7. **Use HTTPS** for all JIRA connections
8. **Regular security audits** of API tokens and permissions

## 📞 Support

For issues specific to JIRA MCP server:

1. Check the troubleshooting section above
2. Review JIRA server logs
3. Test JIRA connectivity manually
4. Verify user permissions
5. Check API token validity
6. Review template documentation

## 🏗️ Architecture & Implementation Details

### MCP Server Implementation

The MCP server (`mcp_server.py`) implements:

1. **JIRA Connection Management**:
   - Support for JIRA Cloud and Server instances
   - API token and basic authentication
   - HTTPX async client with connection pooling
   - Automatic retry logic with exponential backoff

2. **Workflow Management**:
   - File-based caching with TTL (1 hour)
   - Automatic workflow discovery and refresh
   - Comprehensive project metadata extraction
   - Issue type and custom field cataloging

3. **Query Execution**:
   - Security validation (read-only JQL queries)
   - JQL parsing and validation
   - Result caching (5-minute TTL)
   - Query result limiting

4. **LLM Integration**:
   - Server-side prompting templates
   - Action schemas for tool selection
   - JIRA-specific rules and examples
   - Safety constraints and guidelines

5. **MCP Protocol**:
   - FastMCP with streamable-http transport
   - Tool registration (`query_jira`, `refresh_workflows`, `health_check`)
   - Resource registration (`workflows://jira`, `prompts://jira`)

### FastAPI Client Implementation

The FastAPI client (`mcp_client.py`) provides:

1. **MCP Communication**:
   - FastMCP client with streamable-http transport
   - Tool and resource calling capabilities
   - Error handling and logging

2. **REST API Endpoints**:
   - `/query` - Direct JIRA query execution
   - `/workflows` - Get JIRA workflows and metadata
   - `/health` - Health check
   - `/ask_llm` - LLM-powered natural language queries

3. **LLM Integration**:
   - NailLLMLangchain integration
   - Fetches server-side prompts
   - Composes final prompts with user questions
   - Parses LLM JSON actions and executes MCP calls

4. **Request/Response Flow**:
   ```
   User Question → /ask_llm → Fetch prompts://jira → 
   Compose prompt → LLM invoke → Parse JSON action → 
   Execute MCP tool/resource → Return result
   ```

### Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   MCP Server     │    │   JIRA Cloud/   │
│   Client        │◄──►│   (FastMCP)      │◄──►│   Server        │
│   (Port 8001)   │    │   (Port 8000)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   NailLLM       │    │   Workflows      │
│   Langchain     │    │   Cache          │
└─────────────────┘    └──────────────────┘
```

## 🔗 Useful Links

- [JIRA REST API Documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v2/)
- [JQL Reference](https://www.atlassian.com/software/jira/guides/expand-jira/jql)
- [Atlassian API Tokens](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- [JIRA Cloud API](https://developer.atlassian.com/cloud/jira/platform/rest/v2/)
- [JIRA Server API](https://docs.atlassian.com/software/jira/docs/api/REST/8.22.0/)
