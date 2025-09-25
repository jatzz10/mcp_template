# Migration Guide: From Current MySQL MCP to Template

This guide shows how to migrate your current MySQL MCP server implementation to use the new template structure.

## 🎯 Benefits of Migration

- **Multiple Data Sources**: Support MySQL, REST APIs, and custom data sources
- **FastAPI Client**: REST API instead of chat interface
- **Better Architecture**: Modular, testable, and extensible
- **Configuration Management**: YAML-based configuration
- **Enhanced Caching**: Improved performance and reliability

## 📋 Migration Steps

### Step 1: Update Dependencies

```bash
# Add new dependencies to requirements.txt
pip install aiohttp pyyaml
```

### Step 2: Restructure Your Project

```
your-project/
├── template/                    # Template code (copy from this repo)
├── your_server.py              # Your custom server
├── your_client.py              # Your custom client
├── config.yaml                 # Configuration
└── requirements.txt            # Dependencies
```

### Step 3: Create Your Server

```python
# your_server.py
import asyncio
from template.mcp_server.base import MCPServer
from template.mcp_server.datasources.mysql import MySQLDataSource

async def main():
    # Load configuration
    config = {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 8000
    }
    
    # Create server
    server = MCPServer("your-mysql-server", config)
    
    # Add your MySQL data source
    mysql_config = {
        "host": "localhost",
        "user": "your_user",
        "password": "your_password",
        "database": "your_database"
    }
    
    mysql_ds = MySQLDataSource("mysql", mysql_config)
    server.add_data_source("mysql", mysql_ds)
    
    # Start server
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: Create Your FastAPI Client

```python
# your_client.py
from template.mcp_client.fastapi import MCPFastAPIClient
import uvicorn

def main():
    # Create FastAPI client
    client = MCPFastAPIClient(
        server_url="http://127.0.0.1:8000/mcp",
        llm_client=your_llm_client  # Optional
    )
    
    # Get FastAPI app
    app = client.get_app()
    
    # Run server
    uvicorn.run(app, host="127.0.0.1", port=3000)

if __name__ == "__main__":
    main()
```

### Step 5: Add REST API Data Sources (Optional)

```python
# Add REST API data source to your server
from template.mcp_server.datasources.rest_api import RestAPIDataSource

# GitHub API example
github_config = {
    "base_url": "https://api.github.com",
    "auth_type": "bearer",
    "auth_token": "your_github_token"
}

github_ds = RestAPIDataSource("github", github_config)
server.add_data_source("github", github_ds)
```

## 🔄 API Changes

### Old Chat Interface
```python
# Old way
client = MySQLMCPChatClient()
await client.connect()
response = await client.process_command("/query SELECT * FROM users")
```

### New REST API
```python
# New way - HTTP requests
import requests

# Direct query
response = requests.post("http://localhost:3000/query", json={
    "query": "SELECT * FROM users",
    "limit": 100
})

# Natural language
response = requests.post("http://localhost:3000/ask", json={
    "question": "Show me all users",
    "limit": 100
})
```

## 🛠️ Custom Data Sources

Create your own data source by extending `MCPDataSource`:

```python
from template.mcp_server.base.datasource import MCPDataSource

class CustomDataSource(MCPDataSource):
    async def connect(self) -> bool:
        # Your connection logic
        pass
    
    async def get_schema(self) -> Dict[str, Any]:
        # Your schema generation
        pass
    
    async def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Your query execution
        pass
    
    async def validate_query(self, query_params: Dict[str, Any]) -> bool:
        # Your validation logic
        pass
```

## 📊 Configuration

Use YAML configuration instead of environment variables:

```yaml
# config.yaml
server:
  name: "my-server"
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

## 🧪 Testing

```python
# Test your server
import asyncio
from template.examples.mysql_server import main as test_server

# Test your client
from template.examples.fastapi_client import main as test_client
```

## 🚀 Deployment

### Docker Example

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000 3000

CMD ["python", "your_server.py"]
```

### Environment Variables

```bash
# Server
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=password
export MYSQL_DATABASE=my_db

# Client
export LLM_API_KEY=your_key
```

## 🔍 Troubleshooting

### Common Issues

1. **Connection Errors**: Check your data source configuration
2. **Schema Generation**: Ensure your database is accessible
3. **LLM Integration**: Verify your LLM client is properly configured
4. **CORS Issues**: Update CORS origins in client config

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Tips

1. **Caching**: Adjust cache TTL based on your data update frequency
2. **Connection Pooling**: Configure appropriate pool sizes
3. **Rate Limiting**: Set appropriate limits for API data sources
4. **Query Limits**: Use reasonable query limits to prevent large responses

## 🎉 Next Steps

1. **Add More Data Sources**: Integrate additional APIs or databases
2. **Custom Tools**: Add domain-specific MCP tools
3. **Monitoring**: Add metrics and logging
4. **Security**: Implement authentication and authorization
5. **Scaling**: Use load balancers and multiple server instances
