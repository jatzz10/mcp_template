"""
Schema management for MCP servers
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib


class SchemaManager:
    """
    Manages schema caching and persistence for data sources.
    
    Features:
    - File-based schema storage
    - TTL-based cache invalidation
    - Schema versioning
    - Automatic refresh detection
    """
    
    def __init__(self, cache_dir: str = "resources"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_schema_file_path(self, data_source_name: str) -> str:
        """Get the file path for a data source's schema"""
        return os.path.join(self.cache_dir, f"{data_source_name}_schema.json")
    
    def _get_metadata_file_path(self, data_source_name: str) -> str:
        """Get the file path for schema metadata"""
        return os.path.join(self.cache_dir, f"{data_source_name}_metadata.json")
    
    async def get_schema(self, data_source_name: str) -> Optional[Dict[str, Any]]:
        """
        Get cached schema for a data source.
        
        Returns:
            Schema dict if cached and fresh, None otherwise
        """
        schema_file = self._get_schema_file_path(data_source_name)
        metadata_file = self._get_metadata_file_path(data_source_name)
        
        if not os.path.exists(schema_file) or not os.path.exists(metadata_file):
            return None
        
        try:
            # Load metadata to check TTL
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check if schema is still fresh
            generated_at = datetime.fromisoformat(metadata.get('generated_at', ''))
            ttl_seconds = metadata.get('ttl_seconds', 3600)
            
            if datetime.utcnow() - generated_at > timedelta(seconds=ttl_seconds):
                return None  # Schema is stale
            
            # Load schema
            with open(schema_file, 'r') as f:
                return json.load(f)
                
        except Exception:
            return None
    
    async def save_schema(self, data_source_name: str, schema: Dict[str, Any]) -> None:
        """
        Save schema to cache with metadata.
        
        Args:
            data_source_name: Name of the data source
            schema: Schema dictionary to cache
        """
        schema_file = self._get_schema_file_path(data_source_name)
        metadata_file = self._get_metadata_file_path(data_source_name)
        
        try:
            # Save schema
            with open(schema_file, 'w') as f:
                json.dump(schema, f, indent=2)
            
            # Save metadata
            metadata = {
                "data_source": data_source_name,
                "generated_at": datetime.utcnow().isoformat(),
                "ttl_seconds": schema.get("metadata", {}).get("cache_ttl", 3600),
                "schema_size": len(json.dumps(schema)),
                "version": "1.0"
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            raise Exception(f"Failed to save schema for {data_source_name}: {e}")
    
    async def is_schema_stale(self, data_source_name: str) -> bool:
        """
        Check if cached schema is stale.
        
        Returns:
            True if schema is stale or doesn't exist, False if fresh
        """
        cached_schema = await self.get_schema(data_source_name)
        return cached_schema is None
    
    async def invalidate_schema(self, data_source_name: str) -> None:
        """Remove cached schema for a data source"""
        schema_file = self._get_schema_file_path(data_source_name)
        metadata_file = self._get_metadata_file_path(data_source_name)
        
        for file_path in [schema_file, metadata_file]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
    
    async def get_schema_hash(self, data_source_name: str) -> Optional[str]:
        """
        Get hash of cached schema for change detection.
        
        Returns:
            SHA256 hash of schema, None if no cached schema
        """
        schema = await self.get_schema(data_source_name)
        if not schema:
            return None
        
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()
    
    async def list_cached_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        List all cached schemas with their metadata.
        
        Returns:
            Dict mapping data source names to their metadata
        """
        cached_schemas = {}
        
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('_metadata.json'):
                data_source_name = filename.replace('_metadata.json', '')
                
                try:
                    metadata_file = self._get_metadata_file_path(data_source_name)
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Check if schema is fresh
                    generated_at = datetime.fromisoformat(metadata.get('generated_at', ''))
                    ttl_seconds = metadata.get('ttl_seconds', 3600)
                    is_fresh = datetime.utcnow() - generated_at <= timedelta(seconds=ttl_seconds)
                    
                    cached_schemas[data_source_name] = {
                        **metadata,
                        "is_fresh": is_fresh,
                        "schema_file_exists": os.path.exists(self._get_schema_file_path(data_source_name))
                    }
                except Exception:
                    continue
        
        return cached_schemas
    
    async def cleanup_stale_schemas(self) -> int:
        """
        Remove stale schema files.
        
        Returns:
            Number of files removed
        """
        removed_count = 0
        cached_schemas = await self.list_cached_schemas()
        
        for data_source_name, metadata in cached_schemas.items():
            if not metadata.get("is_fresh", False):
                await self.invalidate_schema(data_source_name)
                removed_count += 1
        
        return removed_count
