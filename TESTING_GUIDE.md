# Testing Guide: Template with Current MySQL Setup

This guide will help you test the MCP template with your current MySQL setup.

## 🚀 Quick Test (5 minutes)

### Step 1: Install Template Dependencies

```bash
# Install additional dependencies for the template
pip install aiohttp pyyaml
```

### Step 2: Run the Test Script

```bash
# Test all template components
python test_template.py
```

This will test:
- ✅ MySQL data source connection
- ✅ Schema generation
- ✅ Query execution
- ✅ MCP server creation
- ✅ FastAPI client creation

### Step 3: Start Template Server

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

### Step 4: Test Template Client

In another terminal:
```bash
# Test the template client
python test_template_client.py
```

## 🧪 Detailed Testing

### Test 1: Basic Functionality

```bash
# Test MySQL data source only
python -c "
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path('template')))
from mcp_server.datasources.mysql import MySQLDataSource

async def test():
    ds = MySQLDataSource('mysql', {
        'host': 'localhost',
        'user': 'mcp_test',
        'password': 'mcp_test_password',
        'database': 'mcp_test_db'
    })
    await ds.connect()
    schema = await ds.get_schema()
    print(f'Tables: {schema[\"metadata\"][\"total_tables\"]}')
    await ds.disconnect()

asyncio.run(test())
"
```

### Test 2: Compare with Current Server

Start your current server:
```bash
python mysql_mcp_server.py  # Port 8000
```

Start template server:
```bash
python run_template_server.py  # Port 8002
```

Test both with the same client:
```bash
# Test current server
python test_mcp_client.py

# Test template server
python test_template_client.py
```

### Test 3: FastAPI Client

```bash
# Start template server first
python run_template_server.py

# In another terminal, start FastAPI client
python template/examples/fastapi_client.py
```

Test REST endpoints:
```bash
# Health check
curl http://localhost:3000/health

# List tools
curl http://localhost:3000/tools

# Execute query
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users LIMIT 3", "limit": 10}'

# Get schema
curl http://localhost:3000/schema
```

## 🔍 Troubleshooting

### Issue: Import Errors

```bash
# Make sure you're in the right directory
cd /Users/jatzz/Projects/mysql-mcp-server

# Check Python path
python -c "import sys; print(sys.path)"
```

### Issue: MySQL Connection

```bash
# Check your environment variables
echo $MYSQL_USER
echo $MYSQL_PASSWORD
echo $MYSQL_DATABASE

# Test MySQL connection directly
mysql -h localhost -u mcp_test -p mcp_test_db -e "SELECT 1"
```

### Issue: Port Conflicts

```bash
# Check what's running on ports
lsof -i :8000
lsof -i :8002
lsof -i :3000

# Kill processes if needed
kill -9 <PID>
```

### Issue: Template Server Won't Start

```bash
# Check for missing dependencies
pip install fastmcp aiohttp pyyaml

# Check Python version
python --version  # Should be 3.8+

# Run with debug
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
import run_template_server
"
```

## 📊 Expected Results

### Test Script Output
```
🚀 Testing MCP Template with Current MySQL Setup
🧪 Testing MySQL Data Source...
✅ Connected to MySQL
✅ Schema generated: 5 tables
✅ Query executed: 1 results
✅ MySQL data source test completed successfully!

🧪 Testing MCP Server...
✅ MCP server created with MySQL data source
✅ MCP server test completed successfully!

🧪 Testing FastAPI Client...
✅ FastAPI client created successfully
✅ FastAPI client test completed successfully!

🎉 All tests passed! Template is ready to use.
```

### Template Server Output
```
🚀 Starting Template MCP Server with MySQL
📊 MySQL Config: mcp_test@localhost:3306/mcp_test_db
✅ Server created with data sources: ['mysql']
🌐 Server URL: http://127.0.0.1:8002/mcp
```

### Template Client Output
```
🧪 Testing Template MCP Client
✅ Connected to template server
✅ Query executed successfully
✅ Schema resource retrieved
✅ Template client test completed successfully!
```

## 🎯 Success Criteria

- ✅ All test scripts run without errors
- ✅ Template server starts and connects to MySQL
- ✅ Template client can connect and execute queries
- ✅ Schema generation works (same tables as current setup)
- ✅ Query results match current implementation
- ✅ FastAPI client provides REST endpoints

## 🚀 Next Steps

Once testing passes:

1. **Migrate your current server** to use the template
2. **Add REST API data sources** (GitHub, custom APIs)
3. **Deploy the FastAPI client** for production use
4. **Share the template** with other teams

## 📞 Need Help?

If you encounter issues:

1. Check the error messages carefully
2. Verify your MySQL connection works
3. Ensure all dependencies are installed
4. Check port conflicts
5. Review the migration guide: `template/docs/migration_guide.md`
