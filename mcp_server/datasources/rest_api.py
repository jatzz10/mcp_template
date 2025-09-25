"""
REST API data source implementation for MCP servers
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from urllib.parse import urljoin, urlparse
from ..base.datasource import MCPDataSource

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class RestAPIDataSource(MCPDataSource):
    """
    REST API data source implementation.
    
    Features:
    - Multiple authentication methods
    - Rate limiting
    - Response caching
    - Endpoint discovery
    - Error handling
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.logger = logging.getLogger(f"rest_api_datasource.{name}")
        
        if not HAS_AIOHTTP:
            raise ImportError("aiohttp is required for RestAPIDataSource. Install with: pip install aiohttp")
        
        # API configuration
        self.base_url = config.get('base_url', '').rstrip('/')
        self.auth_type = config.get('auth_type', 'none')  # none, bearer, basic, api_key
        self.auth_token = config.get('auth_token', '')
        self.api_key = config.get('api_key', '')
        self.api_key_header = config.get('api_key_header', 'X-API-Key')
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        
        # Request settings
        self.timeout = config.get('timeout', 30)
        self.rate_limit = config.get('rate_limit', 100)  # requests per minute
        self.retry_attempts = config.get('retry_attempts', 3)
        
        # Schema configuration
        self.schema_endpoint = config.get('schema_endpoint', '/schema')
        self.discovery_endpoint = config.get('discovery_endpoint', '/discovery')
        
        self.session = None
        self._rate_limit_tracker = []
    
    async def connect(self) -> bool:
        """Initialize HTTP session"""
        try:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_auth_headers()
            )
            
            self.connected = True
            self.logger.info(f"Connected to REST API: {self.base_url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to REST API: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Close HTTP session"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.connected = False
            self.logger.info("Disconnected from REST API")
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from REST API: {e}")
            return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {'Content-Type': 'application/json'}
        
        if self.auth_type == 'bearer' and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        elif self.auth_type == 'api_key' and self.api_key:
            headers[self.api_key_header] = self.api_key
        
        return headers
    
    def _get_auth(self) -> Optional[aiohttp.BasicAuth]:
        """Get basic auth if configured"""
        if self.auth_type == 'basic' and self.username and self.password:
            return aiohttp.BasicAuth(self.username, self.password)
        return None
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and retries"""
        if not self.connected:
            await self.connect()
        
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        # Rate limiting
        await self._check_rate_limit()
        
        # Add auth
        auth = self._get_auth()
        if auth:
            kwargs['auth'] = auth
        
        # Retry logic
        last_exception = None
        for attempt in range(self.retry_attempts):
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
            except Exception as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise last_exception
    
    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting"""
        import asyncio
        current_time = datetime.utcnow()
        
        # Remove old requests (older than 1 minute)
        self._rate_limit_tracker = [
            req_time for req_time in self._rate_limit_tracker
            if (current_time - req_time).total_seconds() < 60
        ]
        
        # Check if we're at the limit
        if len(self._rate_limit_tracker) >= self.rate_limit:
            sleep_time = 60 - (current_time - self._rate_limit_tracker[0]).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Add current request
        self._rate_limit_tracker.append(current_time)
    
    async def get_schema(self) -> Dict[str, Any]:
        """Generate API schema from discovery endpoint"""
        try:
            # Try to get schema from dedicated endpoint
            try:
                schema_data = await self._make_request('GET', self.schema_endpoint)
                return {
                    "metadata": {
                        "api_name": self.name,
                        "base_url": self.base_url,
                        "total_endpoints": len(schema_data.get('endpoints', [])),
                        "generated_at": datetime.utcnow().isoformat(),
                        "cache_ttl": self.schema_cache_ttl,
                        "data_source": self.name
                    },
                    "endpoints": schema_data.get('endpoints', []),
                    "models": schema_data.get('models', {}),
                    "authentication": {
                        "type": self.auth_type,
                        "required": self.auth_type != 'none'
                    }
                }
            except Exception:
                # Fallback to discovery endpoint
                pass
            
            # Try discovery endpoint
            try:
                discovery_data = await self._make_request('GET', self.discovery_endpoint)
                endpoints = discovery_data.get('endpoints', [])
            except Exception:
                # Fallback: create basic schema from common endpoints
                endpoints = await self._discover_common_endpoints()
            
            return {
                "metadata": {
                    "api_name": self.name,
                    "base_url": self.base_url,
                    "total_endpoints": len(endpoints),
                    "generated_at": datetime.utcnow().isoformat(),
                    "cache_ttl": self.schema_cache_ttl,
                    "data_source": self.name,
                    "discovery_method": "auto"
                },
                "endpoints": endpoints,
                "authentication": {
                    "type": self.auth_type,
                    "required": self.auth_type != 'none'
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating API schema: {e}")
            raise
    
    async def _discover_common_endpoints(self) -> List[Dict[str, Any]]:
        """Discover common REST API endpoints"""
        common_paths = [
            '/users', '/products', '/orders', '/items', '/data',
            '/api/v1/users', '/api/v1/products', '/api/v1/orders'
        ]
        
        discovered_endpoints = []
        
        for path in common_paths:
            try:
                response = await self._make_request('GET', path)
                if isinstance(response, (list, dict)):
                    discovered_endpoints.append({
                        "path": path,
                        "method": "GET",
                        "description": f"Get {path.split('/')[-1]} data",
                        "response_type": "array" if isinstance(response, list) else "object",
                        "sample_response": response[:3] if isinstance(response, list) else response
                    })
            except Exception:
                continue
        
        return discovered_endpoints
    
    async def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute API query"""
        endpoint = query_params.get('endpoint', '')
        method = query_params.get('method', 'GET').upper()
        params = query_params.get('params', {})
        limit = min(query_params.get('limit', 100), self.max_query_limit)
        
        try:
            # Add limit parameter if not present
            if 'limit' not in params and limit < 1000:
                params['limit'] = limit
            
            response = await self._make_request(method, endpoint, params=params)
            
            # Ensure response is a list
            if isinstance(response, dict):
                # Try to find array data in common keys
                for key in ['data', 'items', 'results', 'records']:
                    if key in response and isinstance(response[key], list):
                        return response[key][:limit]
                # If no array found, wrap the dict
                return [response]
            elif isinstance(response, list):
                return response[:limit]
            else:
                return [{"data": response}]
                
        except Exception as e:
            self.logger.error(f"API query error: {e}")
            raise
    
    async def validate_query(self, query_params: Dict[str, Any]) -> bool:
        """Validate API query parameters"""
        endpoint = query_params.get('endpoint', '')
        method = query_params.get('method', 'GET').upper()
        
        # Basic validation
        if not endpoint:
            return False
        
        # Only allow safe methods
        if method not in ['GET', 'HEAD', 'OPTIONS']:
            return False
        
        # Check limit
        limit = query_params.get('limit', 100)
        if limit > self.max_query_limit:
            return False
        
        # Validate endpoint format
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        # Basic path validation (prevent directory traversal)
        if '..' in endpoint or '//' in endpoint:
            return False
        
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform API health check"""
        try:
            if not self.connected:
                await self.connect()
            
            # Try a simple request to check connectivity
            await self._make_request('GET', '/health')
            
            return {
                "status": "healthy",
                "data_source": self.name,
                "type": "rest_api",
                "connected": self.connected,
                "base_url": self.base_url,
                "auth_type": self.auth_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "data_source": self.name,
                "type": "rest_api",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
