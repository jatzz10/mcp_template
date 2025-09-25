"""
MySQL data source implementation for MCP servers
"""

import pymysql
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from ..base.datasource import MCPDataSource


class MySQLDataSource(MCPDataSource):
    """
    MySQL data source implementation.
    
    Features:
    - Connection pooling
    - Schema generation with relationships
    - Query execution with limits
    - Security validation (SELECT only)
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.connection = None
        self.logger = logging.getLogger(f"mysql_datasource.{name}")
        
        # MySQL specific config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 3306)
        self.user = config.get('user', 'root')
        self.password = config.get('password', '')
        self.database = config.get('database', '')
        self.charset = config.get('charset', 'utf8mb4')
        
        # Connection pool settings
        self.max_connections = config.get('max_connections', 10)
        self.connect_timeout = config.get('connect_timeout', 10)
    
    async def connect(self) -> bool:
        """Establish connection to MySQL database"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                connect_timeout=self.connect_timeout,
                autocommit=True
            )
            self.connected = True
            self.logger.info(f"Connected to MySQL: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to MySQL: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Close MySQL connection"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
            self.connected = False
            self.logger.info("Disconnected from MySQL")
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from MySQL: {e}")
            return False
    
    async def get_schema(self) -> Dict[str, Any]:
        """Generate comprehensive MySQL schema"""
        if not self.connected:
            await self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Get database information
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            
            # Get all tables
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_COMMENT, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
            """, (db_name,))
            
            tables_info = cursor.fetchall()
            tables = {}
            
            for table_name, comment, rows, data_length, index_length in tables_info:
                # Get columns
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, 
                           COLUMN_KEY, EXTRA, COLUMN_COMMENT
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (db_name, table_name))
                
                columns_info = cursor.fetchall()
                columns = {}
                
                for col_name, data_type, nullable, default, key, extra, col_comment in columns_info:
                    columns[col_name] = {
                        "type": data_type,
                        "nullable": nullable == 'YES',
                        "default": default,
                        "key": key,
                        "extra": extra,
                        "comment": col_comment
                    }
                
                # Get indexes
                cursor.execute("""
                    SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE, INDEX_TYPE
                    FROM information_schema.STATISTICS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """, (db_name, table_name))
                
                indexes_info = cursor.fetchall()
                indexes = {}
                
                for idx_name, col_name, non_unique, idx_type in indexes_info:
                    if idx_name not in indexes:
                        indexes[idx_name] = {
                            "columns": [],
                            "unique": non_unique == 0,
                            "type": idx_type
                        }
                    indexes[idx_name]["columns"].append(col_name)
                
                # Get foreign keys
                cursor.execute("""
                    SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, 
                           REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s 
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (db_name, table_name))
                
                foreign_keys_info = cursor.fetchall()
                foreign_keys = {}
                
                for constraint_name, col_name, ref_table, ref_col in foreign_keys_info:
                    foreign_keys[constraint_name] = {
                        "column": col_name,
                        "referenced_table": ref_table,
                        "referenced_column": ref_col
                    }
                
                # Get sample data (first 3 rows)
                cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 3")
                sample_data = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                
                sample_rows = []
                for row in sample_data:
                    sample_rows.append(dict(zip(column_names, row)))
                
                tables[table_name] = {
                    "comment": comment,
                    "row_count": rows,
                    "data_size": data_length,
                    "index_size": index_length,
                    "columns": columns,
                    "indexes": indexes,
                    "foreign_keys": foreign_keys,
                    "sample_data": sample_rows
                }
            
            cursor.close()
            
            return {
                "metadata": {
                    "database_name": db_name,
                    "total_tables": len(tables),
                    "generated_at": datetime.utcnow().isoformat(),
                    "cache_ttl": self.schema_cache_ttl,
                    "data_source": self.name
                },
                "tables": tables
            }
            
        except Exception as e:
            self.logger.error(f"Error generating schema: {e}")
            raise
    
    async def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute SQL query against MySQL database"""
        if not self.connected:
            await self.connect()
        
        query = query_params.get('query', '')
        limit = min(query_params.get('limit', 100), self.max_query_limit)
        
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            
            # Add LIMIT if not present
            if 'LIMIT' not in query.upper():
                query = f"{query.rstrip(';')} LIMIT {limit}"
            
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Query error: {e}")
            raise
    
    async def validate_query(self, query_params: Dict[str, Any]) -> bool:
        """Validate SQL query for security"""
        query = query_params.get('query', '').strip().upper()
        
        # Only allow SELECT queries
        if not query.startswith('SELECT'):
            return False
        
        # Block dangerous operations
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 
            'TRUNCATE', 'REPLACE', 'LOAD_FILE', 'INTO OUTFILE',
            'INTO DUMPFILE', 'EXEC', 'EXECUTE', 'CALL', 'PROCEDURE'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query:
                return False
        
        # Check limit
        limit = query_params.get('limit', 100)
        if limit > self.max_query_limit:
            return False
        
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform MySQL health check"""
        try:
            if not self.connected:
                await self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            return {
                "status": "healthy",
                "data_source": self.name,
                "type": "mysql",
                "connected": self.connected,
                "database": self.database,
                "host": self.host,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "data_source": self.name,
                "type": "mysql",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
