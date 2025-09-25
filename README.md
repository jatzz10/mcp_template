# MCP Server & Client Template

A template for building Model Context Protocol (MCP) servers and clients with support for multiple data sources.

## 🏗️ Architecture

```
template/
├── mcp_server/                 # MCP Server Template
│   ├── base/                   # Abstract base classes
│   ├── datasources/            # Data source implementations
│   │   ├── mysql/              # MySQL data source
│   │   ├── rest_api/           # REST API data source
│   │   └── __init__.py
│   ├── core/                   # Core MCP server logic
│   └── config/                 # Configuration management
├── mcp_client/                 # MCP Client Template
│   ├── fastapi/                # FastAPI REST client
│   ├── chat/                   # Chat client (optional)
│   └── base/                   # Abstract client classes
├── examples/                   # Example implementations
└── docs/                       # Documentation
```

## 🚀 Quick Start

### 1. Create a New MCP Server

```python
from template.mcp_server.base import MCPDataSource, MCPServer
from template.mcp_server.datasources.rest_api import RestAPIDataSource

class MyAPIDataSource(MCPDataSource):
    def __init__(self, config):
        self.api_url = config['api_url']
        self.api_key = config['api_key']
    
    async def get_schema(self):
        # Return your API schema
        pass
    
    async def query(self, query_params):
        # Execute API calls
        pass

# Create server
server = MCPServer("my-api-server")
server.add_data_source("api", MyAPIDataSource(config))
server.run()
```

### 2. Create a FastAPI Client

```python
from template.mcp_client.fastapi import MCPFastAPIClient

app = MCPFastAPIClient(
    server_url="http://localhost:8000/mcp",
    llm_client=your_llm_client
)

# Your FastAPI routes will have access to MCP tools
@app.post("/query")
async def query_endpoint(request: QueryRequest):
    result = await app.mcp_client.call_tool("query_api", request.dict())
    return result
```

## 📋 Data Source Types

### MySQL Data Source
- Schema generation and caching
- Query execution with limits
- Connection pooling

### REST API Data Source
- Endpoint discovery
- Authentication handling
- Rate limiting
- Response caching

### Custom Data Sources
- Implement `MCPDataSource` interface
- Add schema generation
- Define query methods

## 🔧 Configuration

```yaml
# config.yaml
server:
  name: "my-mcp-server"
  transport: "streamable-http"
  port: 8000

datasources:
  mysql:
    enabled: true
    host: "localhost"
    database: "my_db"
  
  rest_api:
    enabled: true
    base_url: "https://api.example.com"
    auth_type: "bearer"
```

## 📚 Best Practices

1. **Schema Caching**: All data sources implement smart caching
2. **Error Handling**: Consistent error responses across all sources
3. **Security**: Input validation and query sanitization
4. **Performance**: Connection pooling and response caching
5. **Monitoring**: Built-in logging and metrics
6. **Testing**: Comprehensive test templates included

## 🧪 Testing

### Quick Test (5 minutes)

```bash
# 1. Install dependencies
pip install aiohttp pyyaml fastapi uvicorn

# 2. Run comprehensive test
python test_template.py

# 3. Start template server
python run_template_server.py

# 4. Test template client (in another terminal)
python test_template_client.py
```

### Detailed Testing Steps

#### Step 1: Test All Components
```bash
# Run the comprehensive test script
python test_template.py
```

Expected output:
```
🚀 Testing MCP Template with Current MySQL Setup
✅ MySQL Data Source: PASS
✅ MCP Server: PASS  
✅ FastAPI Client: PASS
🎉 All tests passed! Template is ready to use.
```

#### Step 2: Start Template Server
```bash
# Start the template MCP server (uses port 8002)
python run_template_server.py
```

You should see:
```
🚀 Starting Template MCP Server with MySQL
📊 MySQL Config: mcp_test@localhost:3306/mcp_test_db
✅ Server created with data sources: ['mysql']
🌐 Server URL: http://127.0.0.1:8002/mcp
```

#### Step 3: Test Template Client
```bash
# In another terminal, test the template client
python test_template_client.py
```

Expected output:
```
🧪 Testing Template MCP Client
✅ Connected to template server
✅ Query executed successfully
✅ Schema resource retrieved
✅ Template client test completed successfully!
```

#### Step 4: Compare with Current Setup
```bash
# Start your current server (port 8000)
python ../mysql_mcp_server.py

# Start template server (port 8002)
python run_template_server.py

# Test both with the same client
python ../test_mcp_client.py  # Tests current server
python test_template_client.py  # Tests template server
```

#### Step 5: Test FastAPI REST Client
```bash
# Start template server first
python run_template_server.py

# In another terminal, start FastAPI client
python examples/fastapi_client.py

# Test REST endpoints
curl http://localhost:3000/health
curl http://localhost:3000/tools
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users LIMIT 3", "limit": 10}'
```

### Test Scripts

- **`test_template.py`**: Comprehensive test of all template components
- **`run_template_server.py`**: Start the template MCP server
- **`test_template_client.py`**: Test the template MCP client
- **`examples/mysql_server.py`**: Example MySQL server implementation
- **`examples/fastapi_client.py`**: Example FastAPI client implementation

### 🔧 Troubleshooting

#### Common Issues

**Import Errors**
```bash
# Make sure you're in the template directory
cd template/

# Install missing dependencies
pip install aiohttp pyyaml fastapi uvicorn
```

**MySQL Connection Issues**
```bash
# Check environment variables
echo $MYSQL_USER
echo $MYSQL_PASSWORD  
echo $MYSQL_DATABASE

# Test MySQL connection directly
mysql -h localhost -u mcp_test -p mcp_test_db -e "SELECT 1"
```

**Port Conflicts**
```bash
# Check what's running on ports
lsof -i :8000
lsof -i :8002
lsof -i :3000

# Kill processes if needed
kill -9 <PID>
```

**Template Server Won't Start**
```bash
# Check dependencies
pip install fastmcp aiohttp pyyaml

# Check Python version (should be 3.8+)
python --version

# Run with debug logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
import run_template_server
"
```

#### Expected Test Results

**Successful Test Output:**
```
🚀 Testing MCP Template with Current MySQL Setup
✅ MySQL Data Source: PASS
✅ MCP Server: PASS
✅ FastAPI Client: PASS
🎉 All tests passed! Template is ready to use.
```

**Template Server Output:**
```
🚀 Starting Template MCP Server with MySQL
📊 MySQL Config: mcp_test@localhost:3306/mcp_test_db
✅ Server created with data sources: ['mysql']
🌐 Server URL: http://127.0.0.1:8002/mcp
```

**Template Client Output:**
```
🧪 Testing Template MCP Client
✅ Connected to template server
✅ Query executed successfully
✅ Schema resource retrieved
✅ Template client test completed successfully!
```

## 📖 Documentation

- [Data Source Development Guide](docs/datasource_guide.md)
- [FastAPI Client Guide](docs/fastapi_client.md)
- [Configuration Reference](docs/configuration.md)
- [Deployment Guide](docs/deployment.md)
