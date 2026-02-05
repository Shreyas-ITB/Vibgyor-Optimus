# Enhanced SQL Database MCP Server

A robust Model Context Protocol (MCP) server for indexing and querying SQL database repositories with advanced features like progress tracking, metadata extraction, and dependency analysis.

## Features

### 🚀 Core Capabilities
- **Fast Indexing**: Efficiently indexes large SQL repositories with progress tracking
- **Smart Search**: Relevance-scored search with support for multiple object types
- **Metadata Extraction**: Automatically extracts columns, parameters, and dependencies
- **Dependency Analysis**: Find relationships between database objects
- **Type Support**: Tables, Views, Stored Procedures, Functions, and Triggers

### 📊 Progress Tracking
- Real-time progress bars in terminal
- ETA calculations for large repositories
- Detailed indexing statistics
- Non-intrusive logging (uses stderr to avoid interfering with MCP JSON)

### 🔍 Advanced Search
- Relevance scoring algorithm
- Multiple object type filtering
- Name pattern matching
- Content snippet extraction
- Configurable result limits

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

```bash
python server.py
```

### Available Tools

#### 1. `load_database`
Index all SQL files from a directory.

**Parameters:**
- `path` (str): Root directory containing SQL files
- `force_reload` (bool, optional): Force re-indexing even if already indexed

**Example:**
```python
load_database(path="D:\\Projects\\VibgyorAI\\database")
```

**Returns:**
```json
{
  "status": "success",
  "message": "Successfully indexed 593 SQL objects",
  "stats": {
    "total_files": 593,
    "total_objects": 593,
    "breakdown": {
      "tables": 250,
      "views": 10,
      "procedures": 300,
      "functions": 25,
      "triggers": 3,
      "unknown": 5
    },
    "failed_files": 0,
    "total_size_mb": 15.43,
    "index_time_seconds": 3.45
  }
}
```

#### 2. `search_sql`
Search indexed SQL objects with relevance scoring.

**Parameters:**
- `query` (str): Search query
- `object_type` (str, optional): Filter by type (table, view, procedure, function)
- `limit` (int, optional): Max results (default: 20, max: 100)

**Example:**
```python
search_sql(query="invoice", object_type="table", limit=10)
```

**Returns:**
```json
{
  "status": "success",
  "query": "invoice",
  "total_results": 3,
  "results": [
    {
      "name": "ScProjectCollectionPayment",
      "type": "table",
      "path": "D:\\...\\ScProjectCollectionPayment.sql",
      "relevance_score": 50.0,
      "line_count": 45,
      "matched_snippet": "...invoice details..."
    }
  ]
}
```

#### 3. `get_sql_file`
Retrieve full SQL file content with optional metadata.

**Parameters:**
- `path` (str): Full file path
- `include_metadata` (bool, optional): Include metadata like columns and parameters

**Example:**
```python
get_sql_file(
    path="D:\\Projects\\VibgyorAI\\database\\BoltDB\\dbo\\Tables\\ScEmployee.sql",
    include_metadata=True
)
```

#### 4. `list_objects`
List SQL objects with filtering options.

**Parameters:**
- `object_type` (str, optional): Filter by type
- `name_pattern` (str, optional): Filter by name (substring match)
- `limit` (int, optional): Max results (default: 100, max: 500)

**Example:**
```python
list_objects(object_type="procedure", name_pattern="Get", limit=50)
```

#### 5. `get_table_schema`
Get detailed schema for a specific table.

**Parameters:**
- `table_name` (str): Name of the table

**Example:**
```python
get_table_schema(table_name="ScEmployee")
```

**Returns:**
```json
{
  "status": "success",
  "table_name": "ScEmployee",
  "path": "D:\\...\\ScEmployee.sql",
  "columns": [
    {"name": "ScEmployeeId", "type": "INT"},
    {"name": "FirstName", "type": "NVARCHAR(50)"},
    {"name": "LastName", "type": "NVARCHAR(50)"}
  ],
  "dependencies": ["ScUser", "ScCompany"],
  "line_count": 65,
  "file_size": 2048
}
```

#### 6. `get_procedure_info`
Get detailed information about a stored procedure.

**Parameters:**
- `procedure_name` (str): Name of the procedure

**Example:**
```python
get_procedure_info(procedure_name="spGetEmployees")
```

#### 7. `get_statistics`
Get current indexing statistics.

**Example:**
```python
get_statistics()
```

#### 8. `find_dependencies`
Find dependency relationships for a database object.

**Parameters:**
- `object_name` (str): Name of the SQL object

**Example:**
```python
find_dependencies(object_name="ScEmployee")
```

**Returns:**
```json
{
  "status": "success",
  "object_name": "ScEmployee",
  "object_type": "table",
  "depends_on": ["ScUser"],
  "dependent_objects": [
    {
      "name": "spGetEmployees",
      "type": "procedure",
      "path": "D:\\...\\spGetEmployees.sql"
    }
  ]
}
```

## Progress Bar Example

When indexing, you'll see progress like this in your terminal:

```
Scanning for SQL files in D:\Projects\VibgyorAI\database...
Found 593 SQL files
Indexing SQL files: |████████████████████████████████████████████████| 593/593 [100.0%] ETA: 0s

✓ Indexing complete!
  Total objects: 593
  Tables: 250, Views: 10, Procedures: 300, Functions: 25
  Time taken: 3.45s
```

## Architecture

### Models (`models.py`)
- `SQLObject`: Represents a SQL database object with metadata
- `SQLObjectType`: Enumeration of SQL object types
- `IndexStats`: Statistics about indexed database
- `SearchResult`: Search result with relevance scoring

### Indexer (`indexer.py`)
- `index_sql_repo()`: Main indexing function with progress tracking
- `detect_object_type_and_name()`: SQL object type detection
- `extract_columns()`: Column metadata extraction
- `extract_parameters()`: Parameter extraction for procedures/functions
- `extract_dependencies()`: Dependency analysis
- `search_objects()`: Advanced search with relevance scoring
- `ProgressBar`: Terminal progress bar implementation

### Server (`server.py`)
- MCP tool implementations
- Global state management
- Error handling and logging
- JSON response formatting

## Performance

- **Indexing Speed**: ~170 files/second
- **Search Speed**: <100ms for most queries
- **Memory Usage**: ~2MB per 100 files indexed
- **Supported Repository Size**: Tested with 500+ files

## Error Handling

All tools return JSON responses with status indicators:
- `"status": "success"` - Operation completed successfully
- `"status": "error"` - Operation failed with error message
- `"status": "already_indexed"` - Database already indexed (for load_database)

## Logging

The server logs to stderr to avoid interfering with MCP's JSON protocol:
- `[INFO]` - Informational messages
- `[ERROR]` - Error messages
- Progress bars and statistics are displayed in real-time

## Best Practices

1. **Initial Load**: Always call `load_database()` first
2. **Re-indexing**: Use `force_reload=True` when database structure changes
3. **Search Optimization**: Use specific object_type filters for faster searches
4. **Large Repositories**: Consider increasing system limits for very large databases

## Troubleshooting

### Progress Bar Not Showing
- Ensure your terminal supports ANSI escape codes
- Progress is written to stderr, check your logging configuration

### Slow Indexing
- Check disk I/O performance
- Consider indexing subsets of the repository
- Use SSD for better performance

### Memory Issues
- The indexer loads file contents into memory
- For very large repositories (1000+ files), consider batching

## License

MIT License - feel free to modify and use in your projects.