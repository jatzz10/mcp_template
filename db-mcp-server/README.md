# Database MCP Server

A complete, production-ready MCP server that connects to various database types including MySQL, PostgreSQL, and SQLite. This server exposes database schemas and query capabilities through the Model Context Protocol (MCP), enabling LLMs to interact with databases safely and efficiently.

## 🎯 What Does This Do?

This MCP server provides:
- **Database Schema Access**: Exposes complete database structure as MCP resources
- **Safe Query Execution**: Allows read-only SQL queries with security validation
- **LLM Integration**: Provides prompting templates for natural language to SQL conversion
- **Caching**: Implements intelligent caching for schemas and query results
- **Multi-Database Support**: Works with MySQL, PostgreSQL, and SQLite
- **FastAPI Client**: Includes a REST API client with `/ask_llm` endpoint for LLM interaction

## 🛠️ Tech Stack & Main Libraries

- **FastMCP**: Modern Python SDK for MCP server/client communication
- **Streamable-HTTP Transport**: Efficient bidirectional HTTP transport for MCP
- **NailLLMLangchain**: LLM integration for natural language processing
- **Database Drivers**: PyMySQL (MySQL), psycopg2-binary (PostgreSQL), sqlite3 (SQLite)
- **FastAPI**: Web framework for the REST API client
- **CacheTools**: In-memory caching for query results
- **Python-dotenv**: Environment variable management

## 🚀 Quick Start

### 1. Copy Template

```bash
cp -r templates/db-mcp-server/ my-database-server/
cd my-database-server/
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit with your database credentials
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
  -d '{"question": "Show me the top 5 users by registration date"}'
```

## 📊 Supported Databases

| Database | Driver | Configuration |
|----------|--------|---------------|
| **MySQL** | PyMySQL | `DB_TYPE=mysql` |
| **PostgreSQL** | psycopg2 | `DB_TYPE=postgresql` |
| **SQLite** | sqlite3 | `DB_TYPE=sqlite` |

## 🔧 Configuration

### Environment Variables

```bash
# Server Configuration
SERVER_NAME=db-mcp-server
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# Database Configuration
DB_TYPE=mysql                    # mysql, postgresql, sqlite
DB_HOST=localhost               # Database host
DB_PORT=3306                    # Database port
DB_USER=root                    # Database user
DB_PASSWORD=password            # Database password
DB_NAME=my_database             # Database name
DB_PATH=/path/to/database.db    # For SQLite only

# Cache Configuration
SCHEMA_CACHE_TTL=3600           # Schema cache TTL (1 hour)
QUERY_CACHE_TTL=300             # Query cache TTL (5 minutes)
MAX_QUERY_LIMIT=1000            # Maximum query results
```

### Database-Specific Setup

#### MySQL
```bash
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_database
```

#### PostgreSQL
```bash
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=your_database
```

#### SQLite
```bash
DB_TYPE=sqlite
DB_PATH=/path/to/your/database.db
# OR
DB_NAME=your_database.db
```

## 📋 MCP Resources

- **`schema://database`** - Complete database schema including:
  - Table structures and column definitions
  - Data types and constraints
  - Indexes and relationships
  - Row counts and statistics

- **`prompts://database`** - LLM prompting templates including:
  - Action schemas for tool/resource selection
  - Domain-specific rules and constraints
  - Example queries and expected responses
  - Safety guidelines for database operations

## 🔧 MCP Tools

- **`query_database`** - Execute SQL queries with:
  - Security validation (SELECT only)
  - Automatic LIMIT enforcement
  - Query result caching
  - Error handling

- **`refresh_schema`** - Refresh schema cache
- **`health_check`** - Check database health

## 🧪 Testing

### Test Server

```bash
# Test database connection
python test_database.py

# Test MCP client
python test_client.py
```

### Example Queries

```python
# Basic query
result = await client.call_tool("query_database", {
    "query": "SELECT * FROM users LIMIT 10",
    "limit": 50
})

# Get table structure
result = await client.call_tool("query_database", {
    "query": "DESCRIBE users",
    "limit": 100
})

# Complex query
result = await client.call_tool("query_database", {
    "query": """
        SELECT u.name, COUNT(p.id) as post_count
        FROM users u
        LEFT JOIN posts p ON u.id = p.user_id
        GROUP BY u.id, u.name
        ORDER BY post_count DESC
    """,
    "limit": 100
})
```

## 🔒 Security Features

### Query Validation

- **Only SELECT queries** are allowed
- **Dangerous keywords** are blocked (DROP, DELETE, INSERT, UPDATE, etc.)
- **Query limits** are enforced
- **SQL injection** prevention

### Blocked Operations

```sql
-- These queries will be rejected:
DROP TABLE users;           -- DROP operations
DELETE FROM users;          -- DELETE operations
INSERT INTO users...;       -- INSERT operations
UPDATE users SET...;        -- UPDATE operations
```

## 📈 Performance

### Caching Strategy

- **Schema caching**: File-based with 1-hour TTL
- **Query caching**: Memory-based with 5-minute TTL
- **Automatic refresh**: When schema becomes stale
- **Manual refresh**: Via `refresh_schema` tool

### Query Optimization

- **Automatic LIMIT**: Added to queries without LIMIT
- **Result limiting**: Maximum 1000 rows per query
- **Connection pooling**: Reused database connections
- **Error handling**: Graceful degradation

## 🐛 Troubleshooting

### Common Issues

1. **Connection Failed**
   ```
   Error: Failed to connect to database
   ```
   - Check database server is running
   - Verify connection credentials
   - Check network connectivity

2. **Permission Denied**
   ```
   Error: Access denied for user
   ```
   - Verify database user permissions
   - Check database access rights
   - Ensure user can SELECT from tables

3. **Schema Generation Failed**
   ```
   Error: Failed to generate schema
   ```
   - Check database exists
   - Verify user has schema access
   - Check for corrupted tables

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python mcp_server.py
```

### Health Check

```python
# Check database health
health = await client.call_tool("health_check")
print(health)
```

## 🔄 Schema Refresh

### Automatic Refresh

The schema is automatically refreshed when:
- Cache file doesn't exist
- Cache is older than TTL (1 hour)
- Schema structure changes detected

### Manual Refresh

```python
# Refresh schema cache
result = await client.call_tool("refresh_schema")
print(result)
```

## 📚 Advanced Usage

### Custom Configuration

```python
# Custom server configuration
config = {
    'server_name': 'my-db-server',
    'db_type': 'postgresql',
    'db_host': 'localhost',
    'db_port': 5432,
    'db_user': 'postgres',
    'db_password': 'password',
    'db_name': 'my_database'
}

server = DatabaseMCPServer(config)
await server.start()
```

### Multiple Databases

```python
# Support multiple database connections
class MultiDatabaseServer:
    def __init__(self):
        self.servers = {}
    
    def add_database(self, name, config):
        self.servers[name] = DatabaseMCPServer(config)
```

## 🎯 Best Practices

1. **Use specific queries** instead of `SELECT *`
2. **Add appropriate LIMITs** to prevent large result sets
3. **Refresh schema** when database structure changes
4. **Monitor query performance** and optimize as needed
5. **Use connection pooling** for high-traffic scenarios
6. **Implement proper error handling** in client applications
7. **Cache query results** when appropriate
8. **Validate queries** before execution

## 🏗️ Architecture & Implementation Details

### MCP Server Implementation

The MCP server (`mcp_server.py`) implements:

1. **Database Connection Management**:
   - Supports MySQL, PostgreSQL, and SQLite
   - Connection pooling and error handling
   - Automatic reconnection on failures

2. **Schema Management**:
   - File-based caching with TTL (1 hour)
   - Automatic schema refresh when stale
   - Comprehensive metadata extraction

3. **Query Execution**:
   - Security validation (SELECT only)
   - Automatic LIMIT enforcement
   - Result caching (5-minute TTL)
   - SQL injection prevention

4. **LLM Integration**:
   - Server-side prompting templates
   - Action schemas for tool selection
   - Domain-specific rules and examples
   - Safety constraints and guidelines

5. **MCP Protocol**:
   - FastMCP with streamable-http transport
   - Tool registration (`query_database`, `refresh_schema`, `health_check`)
   - Resource registration (`schema://database`, `prompts://database`)

### FastAPI Client Implementation

The FastAPI client (`mcp_client.py`) provides:

1. **MCP Communication**:
   - FastMCP client with streamable-http transport
   - Tool and resource calling capabilities
   - Error handling and logging

2. **REST API Endpoints**:
   - `/query` - Direct database query execution
   - `/schema` - Get database schema
   - `/health` - Health check
   - `/ask_llm` - LLM-powered natural language queries

3. **LLM Integration**:
   - NailLLMLangchain integration
   - Fetches server-side prompts
   - Composes final prompts with user questions
   - Parses LLM JSON actions and executes MCP calls

4. **Request/Response Flow**:
   ```
   User Question → /ask_llm → Fetch prompts://database → 
   Compose prompt → LLM invoke → Parse JSON action → 
   Execute MCP tool/resource → Return result
   ```

### Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   MCP Server     │    │   Database      │
│   Client        │◄──►│   (FastMCP)      │◄──►│   (MySQL/PG/    │
│   (Port 8001)   │    │   (Port 8000)    │    │    SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   NailLLM       │    │   Schema Cache   │
│   Langchain     │    │   (File-based)   │
└─────────────────┘    └──────────────────┘
```

## 📞 Support

For issues specific to Database MCP server:

1. Check the troubleshooting section above
2. Review database server logs
3. Test database connectivity manually
4. Verify user permissions
5. Check template documentation
