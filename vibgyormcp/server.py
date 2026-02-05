from fastmcp import FastMCP
from typing import Optional, List, Dict, Any
import json
from pathlib import Path
import sys
import logging
import pyodbc

from indexer import index_sql_repo, search_objects
from models import SQLObject, SQLObjectType, IndexStats


# Configure logging to stderr ONLY (critical for STDIO MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    stream=sys.stderr,  # MUST use stderr for STDIO servers
    force=True
)
logger = logging.getLogger(__name__)


# Initialize MCP server
mcp = FastMCP("Company SQL Database MCP")

# ─────────────────────────────────────────────
# Global state — File Indexer
# ─────────────────────────────────────────────
SQL_INDEX: List[SQLObject] = []
INDEX_STATS: Optional[IndexStats] = None
INDEXED_PATH: Optional[str] = None

# ─────────────────────────────────────────────
# Global state — Live SQL Server Connection
# ─────────────────────────────────────────────
SQL_CONNECTION: Optional[pyodbc.Connection] = None
CURRENT_DATABASE: Optional[str] = None


# ═══════════════════════════════════════════════════════
# SECTION 1: LIVE SQL SERVER TOOLS
# ═══════════════════════════════════════════════════════

def auto_connect():
    global SQL_CONNECTION, CURRENT_DATABASE
    try:
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost\\SQLEXPRESS;"
            "DATABASE=BoltAtom;"
            "Trusted_Connection=yes;"
            "Encrypt=optional;"
        )
        SQL_CONNECTION = pyodbc.connect(conn_str, timeout=15)
        CURRENT_DATABASE = "BoltAtom"
        logger.info("Auto-connected to SQL Server (BoltAtom)")
    except Exception as e:
        logger.error(f"Auto-connect failed: {e}")

@mcp.tool()
def list_databases() -> str:
    """
    List all databases on the connected SQL Server.

    Returns:
        JSON string with database list
    """
    try:
        if not SQL_CONNECTION:
            return json.dumps({"status": "error", "message": "Not connected. Call connect_to_server first."})

        cursor = SQL_CONNECTION.cursor()
        cursor.execute("SELECT name, database_id, state_desc FROM sys.databases ORDER BY name")

        databases = [{"name": r[0], "database_id": r[1], "state": r[2]} for r in cursor.fetchall()]
        cursor.close()

        return json.dumps({"status": "success", "databases": databases}, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


ALLOWED_DATABASES = {"BoltAtom", "HRMS_Dev"}

@mcp.tool()
def switch_database(database_name: str) -> str:
    global CURRENT_DATABASE
    if database_name not in ALLOWED_DATABASES:
        return json.dumps({
            "status": "error",
            "message": f"Database '{database_name}' is not allowed"
        })

    try:
        cursor = SQL_CONNECTION.cursor()
        cursor.execute(f"USE [{database_name}]")
        cursor.close()
        CURRENT_DATABASE = database_name
        return json.dumps({
            "status": "success",
            "current_database": CURRENT_DATABASE
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def list_tables(schema: str = "dbo") -> str:
    """
    List all tables in the current database.

    Args:
        schema: Schema name (default: 'dbo')

    Returns:
        JSON string with table list including row counts
    """
    try:
        if not SQL_CONNECTION:
            return json.dumps({"status": "error", "message": "Not connected. Call connect_to_server first."})

        cursor = SQL_CONNECTION.cursor()
        cursor.execute(f"""
            SELECT
                t.name AS table_name,
                p.rows AS row_count
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            INNER JOIN sys.indexes i ON t.object_id = i.object_id AND i.index_id IN (0,1)
            INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
            WHERE s.name = '{schema}'
            ORDER BY t.name
        """)

        tables = [{"table_name": r[0], "row_count": r[1]} for r in cursor.fetchall()]
        cursor.close()

        return json.dumps({
            "status": "success",
            "database": CURRENT_DATABASE,
            "schema": schema,
            "total_tables": len(tables),
            "tables": tables
        }, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def get_table_columns(table_name: str, schema: str = "dbo") -> str:
    """
    Get column details for a specific table (name, type, nullable, identity, primary key).

    Args:
        table_name: Name of the table
        schema: Schema name (default: 'dbo')

    Returns:
        JSON string with column definitions
    """
    try:
        if not SQL_CONNECTION:
            return json.dumps({"status": "error", "message": "Not connected. Call connect_to_server first."})

        cursor = SQL_CONNECTION.cursor()

        # Columns
        cursor.execute(f"""
            SELECT
                c.name,
                t.name AS data_type,
                c.max_length,
                c.precision,
                c.scale,
                c.is_nullable,
                c.is_identity
            FROM sys.columns c
            INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
            WHERE c.object_id = OBJECT_ID('{schema}.{table_name}')
            ORDER BY c.column_id
        """)
        columns = []
        for r in cursor.fetchall():
            columns.append({
                "column_name": r[0],
                "data_type": r[1],
                "max_length": r[2],
                "precision": r[3],
                "scale": r[4],
                "is_nullable": bool(r[5]),
                "is_identity": bool(r[6])
            })

        # Primary keys
        cursor.execute(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
              AND TABLE_NAME = '{table_name}'
              AND TABLE_SCHEMA = '{schema}'
        """)
        primary_keys = [r[0] for r in cursor.fetchall()]

        # Foreign keys
        cursor.execute(f"""
            SELECT
                fk.name,
                c.name AS column_name,
                OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
                COL_NAME(fk.referenced_object_id, fkc.referenced_column_id) AS referenced_column
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.columns c ON fkc.parent_object_id = c.object_id AND fkc.parent_column_id = c.column_id
            WHERE fk.parent_object_id = OBJECT_ID('{schema}.{table_name}')
        """)
        foreign_keys = [{"constraint": r[0], "column": r[1], "references_table": r[2], "references_column": r[3]} for r in cursor.fetchall()]

        cursor.close()

        return json.dumps({
            "status": "success",
            "database": CURRENT_DATABASE,
            "table": f"{schema}.{table_name}",
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys
        }, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def query_table(
    table_name: str,
    schema: str = "dbo",
    columns: str = "*",
    where_clause: str = "",
    order_by: str = "",
    limit: int = 100
) -> str:
    """
    Query a table with optional filtering, ordering and row limit.
    Use this for simple SELECT queries without writing raw SQL.

    Args:
        table_name: Name of the table to query
        schema: Schema name (default: 'dbo')
        columns: Comma-separated column names or '*' for all (default: '*')
        where_clause: WHERE condition WITHOUT the 'WHERE' keyword (e.g. "CustomerID = 1")
        order_by: Column name to order by (e.g. "CreatedDate DESC")
        limit: Max rows to return (default: 100, max: 5000)

    Returns:
        JSON string with query results
    """
    try:
        if not SQL_CONNECTION:
            return json.dumps({"status": "error", "message": "Not connected. Call connect_to_server first."})

        limit = min(max(1, limit), 5000)

        sql = f"SELECT TOP {limit} {columns} FROM [{schema}].[{table_name}]"
        if where_clause:
            sql += f" WHERE {where_clause}"
        if order_by:
            sql += f" ORDER BY {order_by}"

        logger.info(f"Executing: {sql}")

        cursor = SQL_CONNECTION.cursor()
        cursor.execute(sql)

        col_names = [desc[0] for desc in cursor.description]
        rows = []
        for row in cursor.fetchall():
            rows.append(dict(zip(col_names, [str(v) if v is not None else None for v in row])))

        cursor.close()

        return json.dumps({
            "status": "success",
            "database": CURRENT_DATABASE,
            "table": f"{schema}.{table_name}",
            "sql_executed": sql,
            "row_count": len(rows),
            "columns": col_names,
            "rows": rows
        }, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def execute_query(query: str, max_rows: int = 1000) -> str:
    """
    Execute any raw SQL query against the current database.

    Args:
        query: The full SQL statement to execute
        max_rows: Maximum rows to return for SELECT queries (default: 1000, max: 5000)

    Returns:
        JSON string with results or execution status
    """
    try:
        if not SQL_CONNECTION:
            return json.dumps({"status": "error", "message": "Not connected. Call connect_to_server first."})

        max_rows = min(max(1, max_rows), 5000)

        cursor = SQL_CONNECTION.cursor()
        cursor.execute(query)

        # SELECT — return rows
        if cursor.description:
            col_names = [desc[0] for desc in cursor.description]
            rows = []
            for i, row in enumerate(cursor):
                if i >= max_rows:
                    break
                rows.append(dict(zip(col_names, [str(v) if v is not None else None for v in row])))

            cursor.close()
            return json.dumps({
                "status": "success",
                "database": CURRENT_DATABASE,
                "row_count": len(rows),
                "truncated": len(rows) >= max_rows,
                "columns": col_names,
                "rows": rows
            }, indent=2)

        # Non-SELECT (INSERT / UPDATE / DELETE)
        SQL_CONNECTION.commit()
        cursor.close()
        return json.dumps({"status": "success", "message": "Query executed successfully", "database": CURRENT_DATABASE}, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def search_tables(search_term: str) -> str:
    """
    Search for tables, views, and stored procedures by name.

    Args:
        search_term: Substring to look for in object names

    Returns:
        JSON string with matching objects
    """
    try:
        if not SQL_CONNECTION:
            return json.dumps({"status": "error", "message": "Not connected. Call connect_to_server first."})

        cursor = SQL_CONNECTION.cursor()
        cursor.execute(f"""
            SELECT
                o.name,
                s.name AS schema_name,
                CASE o.type
                    WHEN 'U' THEN 'Table'
                    WHEN 'V' THEN 'View'
                    WHEN 'P' THEN 'Stored Procedure'
                    WHEN 'FN' THEN 'Function'
                    ELSE o.type
                END AS object_type
            FROM sys.objects o
            INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
            WHERE o.name LIKE '%{search_term}%'
              AND o.type IN ('U','V','P','FN')
            ORDER BY o.type, o.name
        """)

        results = [{"name": r[0], "schema": r[1], "type": r[2]} for r in cursor.fetchall()]
        cursor.close()

        return json.dumps({
            "status": "success",
            "database": CURRENT_DATABASE,
            "search_term": search_term,
            "total_results": len(results),
            "results": results
        }, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ═══════════════════════════════════════════════════════
# SECTION 2: ORIGINAL FILE-INDEXER TOOLS  (unchanged)
# ═══════════════════════════════════════════════════════


@mcp.tool()
def load_database(path: str, force_reload: bool = False) -> str:
    """
    Index all SQL files under the given folder path.
    
    Args:
        path: Root directory path containing SQL files
        force_reload: Force re-indexing even if already indexed
        
    Returns:
        JSON string with indexing statistics
    """
    global SQL_INDEX, INDEX_STATS, INDEXED_PATH
    
    try:
        if not force_reload and INDEXED_PATH == path and SQL_INDEX:
            logger.info(f"Database already indexed from {path}")
            return json.dumps({
                "status": "already_indexed",
                "message": f"Database already indexed from {path}. Use force_reload=True to re-index.",
                "stats": INDEX_STATS.to_dict() if INDEX_STATS else {}
            })
        
        logger.info(f"Starting database indexing from: {path}")
        
        if not Path(path).exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        SQL_INDEX, INDEX_STATS = index_sql_repo(path, verbose=True)
        INDEXED_PATH = path
        
        logger.info(f"Indexing completed: {INDEX_STATS.total_objects} objects indexed")
        
        return json.dumps({
            "status": "success",
            "message": f"Successfully indexed {INDEX_STATS.total_objects} SQL objects",
            "stats": INDEX_STATS.to_dict()
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to index database: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to index database: {str(e)}"
        })


@mcp.tool()
def search_sql(
    query: str,
    object_type: str = "",
    limit: int = 20
) -> str:
    """
    Search SQL content by keyword or phrase with relevance scoring.
    
    Args:
        query: Search query (keywords or phrase)
        object_type: Optional filter by type (table, view, procedure, function)
        limit: Maximum number of results (default: 20, max: 100)
        
    Returns:
        JSON string with search results sorted by relevance
    """
    try:
        if not SQL_INDEX:
            return json.dumps({
                "status": "error",
                "message": "No database indexed. Please call load_database first."
            })
        
        limit = min(max(1, limit), 100)
        
        type_filter = None
        if object_type:
            try:
                type_filter = [SQLObjectType(object_type.lower())]
            except ValueError:
                return json.dumps({
                    "status": "error",
                    "message": f"Invalid object_type: {object_type}. Valid types: table, view, procedure, function, trigger"
                })
        
        logger.info(f"Searching for: '{query}' (type: {object_type or 'all'}, limit: {limit})")
        
        results = search_objects(SQL_INDEX, query, limit=limit, object_types=type_filter)
        
        return json.dumps({
            "status": "success",
            "query": query,
            "total_results": len(results),
            "results": results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Search failed: {str(e)}"
        })


@mcp.tool()
def get_sql_file(path: str, include_metadata: bool = False) -> str:
    """
    Get full SQL file content by path.
    
    Args:
        path: Full file path of the SQL file
        include_metadata: Include file metadata (columns, parameters, dependencies)
        
    Returns:
        SQL file content or metadata as JSON string
    """
    try:
        if not SQL_INDEX:
            return json.dumps({
                "status": "error",
                "message": "No database indexed. Please call load_database first."
            })
        
        for obj in SQL_INDEX:
            if obj.path == path:
                if include_metadata:
                    return json.dumps({
                        "status": "success",
                        "name": obj.name,
                        "type": obj.type.value,
                        "path": obj.path,
                        "file_size": obj.file_size,
                        "line_count": obj.line_count,
                        "modified_at": obj.modified_at.isoformat() if obj.modified_at else None,
                        "columns": obj.columns,
                        "parameters": obj.parameters,
                        "dependencies": obj.dependencies,
                        "content": obj.content
                    }, indent=2)
                else:
                    return obj.content
        
        return json.dumps({
            "status": "error",
            "message": f"SQL file not found: {path}"
        })
        
    except Exception as e:
        logger.error(f"Failed to get SQL file: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to get SQL file: {str(e)}"
        })


@mcp.tool()
def list_objects(
    object_type: str = "",
    name_pattern: str = "",
    limit: int = 100
) -> str:
    """
    List SQL objects with optional filtering.
    
    Args:
        object_type: Filter by type (table, view, procedure, function, trigger)
        name_pattern: Filter by name pattern (case-insensitive substring match)
        limit: Maximum number of results (default: 100, max: 500)
        
    Returns:
        JSON string with list of SQL objects
    """
    try:
        if not SQL_INDEX:
            return json.dumps({
                "status": "error",
                "message": "No database indexed. Please call load_database first."
            })
        
        limit = min(max(1, limit), 500)
        
        results = []
        name_pattern_lower = name_pattern.lower() if name_pattern else ""
        
        for obj in SQL_INDEX:
            if object_type and obj.type.value != object_type.lower():
                continue
            if name_pattern_lower and name_pattern_lower not in obj.name.lower():
                continue
            
            results.append({
                "name": obj.name,
                "type": obj.type.value,
                "path": obj.path,
                "file_size": obj.file_size,
                "line_count": obj.line_count
            })
            
            if len(results) >= limit:
                break
        
        return json.dumps({
            "status": "success",
            "total_results": len(results),
            "filters": {
                "object_type": object_type or "all",
                "name_pattern": name_pattern or "none"
            },
            "results": results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to list objects: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to list objects: {str(e)}"
        })


@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """
    Get detailed schema information for a specific table from the file index.
    
    Args:
        table_name: Name of the table
        
    Returns:
        JSON string with table schema details
    """
    try:
        if not SQL_INDEX:
            return json.dumps({
                "status": "error",
                "message": "No database indexed. Please call load_database first."
            })
        
        for obj in SQL_INDEX:
            if obj.type == SQLObjectType.TABLE and obj.name.lower() == table_name.lower():
                return json.dumps({
                    "status": "success",
                    "table_name": obj.name,
                    "path": obj.path,
                    "columns": obj.columns,
                    "dependencies": obj.dependencies,
                    "line_count": obj.line_count,
                    "file_size": obj.file_size
                }, indent=2)
        
        return json.dumps({
            "status": "error",
            "message": f"Table not found: {table_name}"
        })
        
    except Exception as e:
        logger.error(f"Failed to get table schema: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to get table schema: {str(e)}"
        })


@mcp.tool()
def get_procedure_info(procedure_name: str) -> str:
    """
    Get detailed information about a stored procedure.
    
    Args:
        procedure_name: Name of the stored procedure
        
    Returns:
        JSON string with procedure details
    """
    try:
        if not SQL_INDEX:
            return json.dumps({
                "status": "error",
                "message": "No database indexed. Please call load_database first."
            })
        
        for obj in SQL_INDEX:
            if obj.type == SQLObjectType.PROCEDURE and obj.name.lower() == procedure_name.lower():
                return json.dumps({
                    "status": "success",
                    "procedure_name": obj.name,
                    "path": obj.path,
                    "parameters": obj.parameters,
                    "dependencies": obj.dependencies,
                    "line_count": obj.line_count,
                    "content": obj.content
                }, indent=2)
        
        return json.dumps({
            "status": "error",
            "message": f"Procedure not found: {procedure_name}"
        })
        
    except Exception as e:
        logger.error(f"Failed to get procedure info: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to get procedure info: {str(e)}"
        })


@mcp.tool()
def get_statistics() -> str:
    """
    Get current database index statistics.
    
    Returns:
        JSON string with indexing statistics
    """
    try:
        if not INDEX_STATS:
            return json.dumps({
                "status": "error",
                "message": "No database indexed. Please call load_database first."
            })
        
        stats_dict = INDEX_STATS.to_dict()
        stats_dict["indexed_path"] = INDEXED_PATH
        stats_dict["status"] = "success"
        
        return json.dumps(stats_dict, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to get statistics: {str(e)}"
        })


@mcp.tool()
def find_dependencies(object_name: str) -> str:
    """
    Find all objects that depend on or are depended upon by the given object.
    
    Args:
        object_name: Name of the SQL object
        
    Returns:
        JSON string with dependency information
    """
    try:
        if not SQL_INDEX:
            return json.dumps({
                "status": "error",
                "message": "No database indexed. Please call load_database first."
            })
        
        target_obj = None
        for obj in SQL_INDEX:
            if obj.name.lower() == object_name.lower():
                target_obj = obj
                break
        
        if not target_obj:
            return json.dumps({
                "status": "error",
                "message": f"Object not found: {object_name}"
            })
        
        depends_on = target_obj.dependencies
        dependent_objects = []
        
        for obj in SQL_INDEX:
            if target_obj.name in obj.dependencies:
                dependent_objects.append({
                    "name": obj.name,
                    "type": obj.type.value,
                    "path": obj.path
                })
        
        return json.dumps({
            "status": "success",
            "object_name": target_obj.name,
            "object_type": target_obj.type.value,
            "depends_on": depends_on,
            "dependent_objects": dependent_objects
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to find dependencies: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to find dependencies: {str(e)}"
        })


# ═══════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("Starting Company SQL Database MCP Server...")
    auto_connect()
    logger.info("")
    logger.info("── Live SQL Server Tools ──")
    logger.info("  - list_databases      : List all databases")
    logger.info("  - switch_database     : Switch active database")
    logger.info("  - list_tables         : List tables (with row counts)")
    logger.info("  - get_table_columns   : Get columns / PKs / FKs")
    logger.info("  - query_table         : Query a table (no raw SQL needed)")
    logger.info("  - execute_query       : Run any raw SQL query")
    logger.info("  - search_tables       : Search objects by name")
    logger.info("")
    logger.info("── File-Indexer Tools ──")
    logger.info("  - load_database       : Index .sql files from a folder")
    logger.info("  - search_sql          : Search indexed .sql content")
    logger.info("  - get_sql_file        : Read a .sql file")
    logger.info("  - list_objects        : List indexed objects")
    logger.info("  - get_table_schema    : Schema from indexed files")
    logger.info("  - get_procedure_info  : Procedure from indexed files")
    logger.info("  - get_statistics      : Indexing stats")
    logger.info("  - find_dependencies   : Object dependency graph")
    logger.info("")

    app = mcp.http_app()
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )