#!/usr/bin/env python3
"""
JIRA MCP Server

A complete, production-ready MCP server that connects to JIRA.

Features:
- Project and issue management
- Workflow and custom field access
- JQL query support
- User and permission information
- Static data resources (JIRA workflows)
- Health monitoring
- Configurable via environment variables

Usage:
    python mcp_server.py

Environment Variables:
    JIRA_BASE_URL=https://your-domain.atlassian.net
    JIRA_USERNAME=your-email@example.com
    JIRA_API_TOKEN=your-api-token
    JIRA_PROJECT_KEY=PROJ
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime

from fastmcp import FastMCP
from cachetools import TTLCache

try:
    from jira import JIRA, JIRAError
    HAS_JIRA = True
except ImportError:
    HAS_JIRA = False


class JiraMCPServer:
    """
    JIRA MCP Server implementation.
    
    This server provides:
    - JIRA workflows as MCP resource (workflows://jira)
    - JIRA query tool (query_jira)
    - Workflow refresh tool (refresh_workflows)
    - Health monitoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_config()
        self.mcp = FastMCP(name=self.config.get('server_name', 'jira-mcp-server'))
        self.jira_client = None
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute cache
        
        if not HAS_JIRA:
            raise ImportError("jira library is required. Install with: pip install jira")
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.get('log_level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("jira_mcp_server")
        
        # Register MCP tools and resources
        self._register_tools()
        self._register_resources()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'server_name': os.getenv('SERVER_NAME', 'jira-mcp-server'),
            'server_host': os.getenv('SERVER_HOST', '127.0.0.1'),
            'server_port': int(os.getenv('SERVER_PORT', '8000')),
            'jira_base_url': os.getenv('JIRA_BASE_URL', ''),
            'jira_username': os.getenv('JIRA_USERNAME', ''),
            'jira_api_token': os.getenv('JIRA_API_TOKEN', ''),
            'jira_project_key': os.getenv('JIRA_PROJECT_KEY', ''),
            'jira_timeout': int(os.getenv('JIRA_TIMEOUT', '30')),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'workflows_cache_ttl': int(os.getenv('WORKFLOWS_CACHE_TTL', '3600')),
            'query_cache_ttl': int(os.getenv('QUERY_CACHE_TTL', '300')),
            'max_query_limit': int(os.getenv('MAX_QUERY_LIMIT', '1000'))
        }
    
    async def connect(self) -> bool:
        """Establish connection to JIRA"""
        try:
            self.jira_client = JIRA(
                server=self.config['jira_base_url'],
                basic_auth=(self.config['jira_username'], self.config['jira_api_token'])
            )
            
            # Test connection by getting current user
            self.jira_client.myself()
            
            self.logger.info(f"Connected to JIRA: {self.config['jira_base_url']}")
            return True
            
        except JIRAError as e:
            self.logger.error(f"Failed to connect to JIRA: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during JIRA connection: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Close JIRA connection"""
        try:
            if self.jira_client:
                # JIRA client doesn't have explicit close method
                self.jira_client = None
            self.logger.info("Disconnected from JIRA")
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from JIRA: {e}")
            return False
    
    async def get_workflows(self) -> Dict[str, Any]:
        """Generate JIRA workflows and metadata"""
        if not self.jira_client:
            await self.connect()
        
        try:
            # Get project information
            project = self.jira_client.project(self.config['jira_project_key'])
            
            # Get issue types
            issue_types = self.jira_client.issue_types()
            
            # Get custom fields
            fields = self.jira_client.fields()
            
            # Get project components
            components = project.components if hasattr(project, 'components') else []
            
            # Get project versions
            versions = project.versions if hasattr(project, 'versions') else []
            
            # Get workflows (simplified approach)
            workflows = await self._get_workflow_info()
            
            return {
                "metadata": {
                    "project_key": self.config['jira_project_key'],
                    "base_url": self.config['jira_base_url'],
                    "generated_at": datetime.utcnow().isoformat(),
                    "cache_ttl": self.config['workflows_cache_ttl']
                },
                "project": {
                    "id": project.id,
                    "key": project.key,
                    "name": project.name,
                    "description": project.description,
                    "url": project.self,
                    "lead": project.lead.displayName if project.lead else None,
                    "components": [{"id": c.id, "name": c.name, "description": c.description} for c in components],
                    "versions": [{"id": v.id, "name": v.name, "description": v.description} for v in versions]
                },
                "issue_types": [
                    {
                        "id": it.id,
                        "name": it.name,
                        "description": it.description,
                        "subtask": it.subtask
                    } for it in issue_types
                ],
                "fields": [
                    {
                        "id": f['id'],
                        "name": f['name'],
                        "custom": f['custom'],
                        "schema": f['schema']
                    } for f in fields
                ],
                "workflows": workflows
            }
            
        except JIRAError as e:
            self.logger.error(f"Error generating JIRA workflows: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error generating JIRA workflows: {e}")
            raise
    
    async def _get_workflow_info(self) -> list:
        """Get workflow information (simplified)"""
        try:
            # This is a simplified approach to get workflow information
            # The actual JIRA API for workflows is complex and often requires admin permissions
            
            workflows = []
            
            # Try to get workflow schemes
            try:
                # This might require admin permissions
                workflow_schemes = self.jira_client._get_json('workflowscheme')
                for scheme in workflow_schemes.get('values', []):
                    workflows.append({
                        "id": scheme.get('id'),
                        "name": scheme.get('name'),
                        "description": scheme.get('description'),
                        "defaultWorkflow": scheme.get('defaultWorkflow', {}).get('name')
                    })
            except JIRAError as e:
                self.logger.warning(f"Could not fetch detailed workflow schemes: {e}")
                # Fallback: create basic workflow info
                workflows.append({
                    "name": "Default Workflow",
                    "description": "Default project workflow",
                    "note": "Detailed workflow information requires admin permissions"
                })
            
            return workflows
            
        except Exception as e:
            self.logger.warning(f"Error getting workflow info: {e}")
            return [{"error": "Could not fetch workflow information"}]
    
    async def execute_query(self, query_type: str, jql: str = "", issue_key: str = "", limit: int = 100) -> list:
        """Execute JIRA query"""
        if not self.jira_client:
            await self.connect()
        
        try:
            if query_type == 'search':
                # Use provided JQL or default project query
                if not jql:
                    jql = f'project = "{self.config["jira_project_key"]}" ORDER BY created DESC'
                
                # Validate JQL
                if not await self.validate_query(query_type, jql, limit):
                    raise ValueError("Invalid JQL query")
                
                issues = self.jira_client.search_issues(jql, maxResults=limit)
                return [issue.raw for issue in issues]
                
            elif query_type == 'issue':
                if not issue_key:
                    raise ValueError("Issue key is required for issue query")
                
                issue = self.jira_client.issue(issue_key)
                return [issue.raw]
                
            elif query_type == 'components':
                project = self.jira_client.project(self.config['jira_project_key'])
                components = [{"id": c.id, "name": c.name, "description": c.description} for c in project.components]
                return components[:limit]
                
            elif query_type == 'versions':
                project = self.jira_client.project(self.config['jira_project_key'])
                versions = [{"id": v.id, "name": v.name, "description": v.description} for v in project.versions]
                return versions[:limit]
                
            else:
                raise ValueError(f"Unknown query type: {query_type}")
                
        except JIRAError as e:
            self.logger.error(f"JIRA query error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during JIRA query: {e}")
            raise
    
    async def validate_query(self, query_type: str, jql: str, limit: int) -> bool:
        """Validate JIRA query parameters"""
        # Validate query type
        if query_type not in ['search', 'issue', 'components', 'versions']:
            return False
        
        # Validate limit
        if limit > self.config['max_query_limit']:
            return False
        
        # For search queries, validate JQL
        if query_type == 'search' and jql:
            # Basic JQL validation
            jql_upper = jql.upper()
            
            # Block dangerous operations
            dangerous_keywords = ['DELETE', 'UPDATE', 'CREATE', 'DROP', 'ALTER']
            for keyword in dangerous_keywords:
                if keyword in jql_upper:
                    return False
            
            # Ensure it's a SELECT-like query (JQL doesn't have explicit SELECT)
            # Just check that it doesn't contain modification keywords
        
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform JIRA health check"""
        try:
            if not self.jira_client:
                await self.connect()
            
            # Test connection by getting project info
            project = self.jira_client.project(self.config['jira_project_key'])
            
            return {
                "status": "healthy",
                "base_url": self.config['jira_base_url'],
                "project_key": self.config['jira_project_key'],
                "project_name": project.name,
                "connected": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "base_url": self.config['jira_base_url'],
                "project_key": self.config['jira_project_key'],
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _register_tools(self) -> None:
        """Register MCP tools"""
        
        @self.mcp.tool()
        async def query_jira(query_type: str, jql: str = "", issue_key: str = "", limit: int = 100) -> str:
            """Execute JIRA query"""
            try:
                # Check cache
                cache_key = f"jira:{query_type}:{jql}:{issue_key}:{limit}"
                if cache_key in self.cache:
                    return self.cache[cache_key]
                
                # Execute query
                results = await self.execute_query(query_type, jql, issue_key, limit)
                
                # Cache result
                result_json = json.dumps(results, indent=2)
                self.cache[cache_key] = result_json
                
                return result_json
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def refresh_workflows() -> str:
            """Refresh JIRA workflows cache"""
            try:
                workflows = await self.get_workflows()
                return json.dumps({
                    "status": "success",
                    "generated_at": workflows["metadata"]["generated_at"],
                    "project_key": workflows["metadata"]["project_key"]
                })
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def health_check() -> str:
            """Check JIRA health"""
            health = await self.health_check()
            return json.dumps(health, indent=2)
    
    def _register_resources(self) -> None:
        """Register MCP resources"""
        
        @self.mcp.resource("workflows://jira")
        async def jira_workflows():
            """Get JIRA workflows and metadata"""
            try:
                workflows = await self.get_workflows()
                return json.dumps(workflows, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.resource("server://info")
        async def server_info():
            """Get server information"""
            return json.dumps({
                "name": self.config['server_name'],
                "jira_base_url": self.config['jira_base_url'],
                "project_key": self.config['jira_project_key'],
                "version": "1.0.0",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        @self.mcp.resource("prompts://jira")
        async def jira_prompts():
            """Get JIRA-specific prompting templates and rules
            
            This resource provides LLM prompting templates specifically designed for JIRA operations.
            Includes action schemas, safety constraints, and JIRA-specific guidance.
            """
            try:
                prompts = {
                    "action_schema": self.build_action_schema_prompt(),
                    "domain_rules": self.build_domain_prompt({}),
                    "fallback_prompt": self.build_fallback_prompt(),
                    "examples": [
                        {
                            "question": "Show me open issues in the project",
                            "expected_action": {
                                "action": "call_tool",
                                "tool": "query_jira",
                                "args": {
                                    "jql": "project = 'PROJ' AND status = 'Open'",
                                    "fields": "summary,status,assignee,created",
                                    "limit": 20
                                }
                            }
                        },
                        {
                            "question": "What workflows are available?",
                            "expected_action": {
                                "action": "read_resource",
                                "uri": "workflows://jira"
                            }
                        }
                    ]
                }
                return json.dumps(prompts, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    # Prompting Methods for LLM Integration
    def build_tool_prompt(self, question: str, tools_meta: Dict[str, Any], resource_meta: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Create a comprehensive tool-aware prompt for JIRA operations
        
        Args:
            question: User's question about JIRA
            tools_meta: Available tools metadata
            resource_meta: Available resources metadata  
            context: Additional context (workflows, etc.)
        
        Returns:
            Formatted prompt string for LLM
        """
        context = context or {}
        workflows_text = context.get('workflows_text', '')
        
        return (
            "You are a JIRA assistant that can query JIRA issues and access workflow information via MCP.\n\n"
            
            "AVAILABLE TOOLS:\n" +
            "\n".join([f"- {t['name']}: {t['description']}" for t in tools_meta.get("tools", [])]) + "\n\n" +
            
            "AVAILABLE RESOURCES:\n" +
            "\n".join([f"- {r['uri']}: {r['description']}" for r in resource_meta.get("resources", [])]) + "\n\n" +
            
            "JIRA WORKFLOWS:\n" + (workflows_text[:15000] if workflows_text else "Workflows not available") + "\n\n" +
            
            "USER QUESTION: " + question + "\n\n" +
            
            "RULES:\n"
            "- Only read operations are allowed. No issue creation, modification, or deletion.\n"
            "- When querying JIRA, call tool 'query_jira' with appropriate JQL query.\n"
            "- If the user asks about workflows/projects, read resource 'workflows://jira'.\n"
            "- Always use proper JQL syntax and respect JIRA constraints.\n"
            "- Limit results appropriately using the limit parameter.\n"
            "- Use appropriate field selections for performance.\n\n" +
            
            "OUTPUT FORMAT:\n"
            "You must respond with a single-line minified JSON object with this exact structure:\n"
            "{\"action\": \"call_tool|read_resource\", \"tool\": \"tool_name\", \"args\": {...}}\n"
            "or {\"action\": \"read_resource\", \"uri\": \"resource_uri\"}\n\n" +
            
            "EXAMPLES:\n"
            "Question: 'Show me open issues in the project'\n"
            "Response: {\"action\": \"call_tool\", \"tool\": \"query_jira\", \"args\": {\"jql\": \"project = 'PROJ' AND status = 'Open'\", \"fields\": \"summary,status,assignee\", \"limit\": 20}}\n\n"
            "Question: 'What workflows are available?'\n"
            "Response: {\"action\": \"read_resource\", \"uri\": \"workflows://jira\"}\n\n" +
            
            "IMPORTANT: Return ONLY the JSON object. No explanations, no markdown, no additional text."
        )
    
    def build_action_schema_prompt(self) -> str:
        """Get the strict JSON action schema for JIRA operations"""
        return (
            "You must respond with a single-line minified JSON object with this exact structure:\n\n"
            "For tool calls:\n"
            "{\"action\": \"call_tool\", \"tool\": \"query_jira\", \"args\": {\"jql\": \"JQL query\", \"fields\": \"field1,field2\", \"limit\": 100}}\n\n"
            "For resource access:\n"
            "{\"action\": \"read_resource\", \"uri\": \"workflows://jira\"}\n\n"
            "Valid tools: query_jira, refresh_workflows, health_check\n"
            "Valid resources: workflows://jira, server://info, prompts://jira\n"
            "Only read operations allowed. No issue creation, modification, or deletion."
        )
    
    def build_domain_prompt(self, context: Dict[str, Any] = None) -> str:
        """Get JIRA-specific domain rules and guidance"""
        context = context or {}
        jira_url = self.config.get('jira_base_url', 'https://jira.example.com')
        project_key = self.config.get('jira_project_key', 'PROJ')
        
        return (
            f"JIRA Domain Rules for {jira_url}:\n\n"
            
            "SAFETY CONSTRAINTS:\n"
            "- Only read operations are allowed\n"
            "- No issue creation, modification, or deletion\n"
            "- No workflow transitions or status changes\n"
            "- No comment addition or modification\n"
            "- No attachment uploads or downloads\n"
            "- No user or permission management\n"
            "- Always use appropriate result limits\n\n"
            
            "JQL (JIRA Query Language) GUIDELINES:\n"
            "- Use proper JQL syntax and operators\n"
            "- Common operators: =, !=, IN, NOT IN, ~, !~, >, <, >=, <=\n"
            "- Logical operators: AND, OR, NOT\n"
            "- Use parentheses for complex queries\n"
            "- Field names are case-sensitive\n"
            "- Use quotes for text values with spaces\n\n"
            
            "COMMON JQL PATTERNS:\n"
            f"- Project issues: project = '{project_key}'\n"
            "- Status filtering: status = 'Open' OR status = 'In Progress'\n"
            "- Assignee filtering: assignee = 'username' OR assignee in (user1, user2)\n"
            "- Date filtering: created >= '2024-01-01' AND created <= '2024-12-31'\n"
            "- Text search: summary ~ 'search term' OR description ~ 'search term'\n"
            "- Issue type: issuetype = 'Bug' OR issuetype = 'Task'\n"
            "- Priority: priority = 'High' OR priority = 'Critical'\n\n"
            
            "FIELD SELECTION:\n"
            "- Common fields: summary, status, assignee, reporter, created, updated, priority, issuetype\n"
            "- Custom fields: Use field names from workflow metadata\n"
            "- Limit fields for better performance\n"
            "- Use '*' for all fields (not recommended for large result sets)\n\n"
            
            f"PROJECT CONTEXT:\n"
            f"- Project key: {project_key}\n"
            f"- Base URL: {jira_url}\n"
            f"- Authentication: Handled automatically\n"
            f"- Rate limiting: Respect API limits\n\n"
            
            "ERROR HANDLING:\n"
            "- If JQL is invalid, suggest checking syntax\n"
            "- If field doesn't exist, suggest checking available fields\n"
            "- If project doesn't exist, suggest checking project key\n"
            "- Always validate JQL against available fields and values"
        )
    
    def build_fallback_prompt(self) -> str:
        """Get fallback prompt for when LLM response isn't valid JSON"""
        return (
            "If the LLM response is not valid JSON or doesn't follow the action schema:\n\n"
            "1. Try to extract a JQL query from the response\n"
            "2. If no valid JQL found, ask user to rephrase\n"
            "3. Suggest using /workflows to check available fields and values\n"
            "4. Provide example JQL queries based on available workflows\n\n"
            "Common fallback patterns:\n"
            "- 'project = \"PROJ\"' for project issues\n"
            "- 'status = \"Open\"' for open issues\n"
            "- 'assignee = \"username\"' for user's issues\n"
            "- 'created >= \"2024-01-01\"' for recent issues\n"
            "- Use limit parameter for large result sets"
        )

    async def start(self) -> None:
        """Start the MCP server"""
        self.logger.info(f"Starting JIRA MCP Server: {self.config['server_name']}")
        
        # Connect to JIRA
        await self.connect()
        
        # Start server
        host = self.config['server_host']
        port = self.config['server_port']
        
        self.logger.info(f"Server ready on {host}:{port} with streamable-http transport")
        self.mcp.run(transport="streamable-http", host=host, port=port)
    
    async def stop(self) -> None:
        """Stop the MCP server"""
        self.logger.info(f"Stopping JIRA MCP Server: {self.config['server_name']}")
        await self.disconnect()
    
    def print_server_info(self) -> None:
        """Print server information"""
        print("\n" + "="*60)
        print("🚀 JIRA MCP Server")
        print("="*60)
        print(f"📊 JIRA Base URL: {self.config['jira_base_url']}")
        print(f"🔗 Resource: workflows://jira")
        print(f"🛠️  Tools: query_jira, refresh_workflows, health_check")
        print(f"🌐 Transport: streamable-http")
        
        print(f"\n📡 Server Endpoint:")
        print(f"   http://{self.config['server_host']}:{self.config['server_port']}/mcp")
        
        print(f"\n🎯 JIRA Connection:")
        print(f"   Base URL: {self.config['jira_base_url']}")
        print(f"   Username: {self.config['jira_username']}")
        print(f"   Project Key: {self.config['jira_project_key']}")
        
        print(f"\n📋 Available MCP Resources:")
        print(f"   • workflows://jira - Complete JIRA workflows and metadata")
        
        print(f"\n🔧 Available MCP Tools:")
        print(f"   • query_jira - Execute JIRA queries")
        print(f"   • refresh_workflows - Refresh workflows cache")
        print(f"   • health_check - Check JIRA health")
        
        print(f"\n📝 Query Types:")
        print(f"   • search - Search issues using JQL")
        print(f"   • issue - Get specific issue details")
        print(f"   • components - Get project components")
        print(f"   • versions - Get project versions")
        
        print("\n" + "="*60)


async def main():
    """Main entry point"""
    try:
        # Create and start server
        server = JiraMCPServer()
        
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
