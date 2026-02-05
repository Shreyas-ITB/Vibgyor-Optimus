from pathlib import Path
from typing import List, Tuple, Optional
import re
import time
from datetime import datetime
import sys

from models import SQLObject, SQLObjectType, IndexStats


# Enhanced SQL patterns with more robust matching
SQL_PATTERNS = {
    SQLObjectType.TABLE: re.compile(
        r"CREATE\s+TABLE\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?",
        re.IGNORECASE | re.MULTILINE
    ),
    SQLObjectType.VIEW: re.compile(
        r"CREATE\s+(?:OR\s+ALTER\s+)?VIEW\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?",
        re.IGNORECASE | re.MULTILINE
    ),
    SQLObjectType.PROCEDURE: re.compile(
        r"CREATE\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?",
        re.IGNORECASE | re.MULTILINE
    ),
    SQLObjectType.FUNCTION: re.compile(
        r"CREATE\s+(?:OR\s+ALTER\s+)?FUNCTION\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?",
        re.IGNORECASE | re.MULTILINE
    ),
    SQLObjectType.TRIGGER: re.compile(
        r"CREATE\s+(?:OR\s+ALTER\s+)?TRIGGER\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?",
        re.IGNORECASE | re.MULTILINE
    ),
}


class ProgressBar:
    """Simple progress bar for terminal display"""
    
    def __init__(self, total: int, desc: str = "Processing", width: int = 50):
        self.total = total
        self.current = 0
        self.desc = desc
        self.width = width
        self.start_time = time.time()
        
    def update(self, n: int = 1):
        """Update progress by n items"""
        self.current += n
        self._render()
        
    def _render(self):
        """Render the progress bar"""
        if self.total == 0:
            percentage = 100
            filled = self.width
        else:
            percentage = (self.current / self.total) * 100
            filled = int((self.current / self.total) * self.width)
        
        bar = '█' * filled + '░' * (self.width - filled)
        elapsed = time.time() - self.start_time
        
        # Calculate ETA
        if self.current > 0:
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            eta_str = f"ETA: {int(remaining)}s"
        else:
            eta_str = "ETA: --"
        
        # Write to stderr to avoid interfering with MCP JSON output
        sys.stderr.write(f'\r{self.desc}: |{bar}| {self.current}/{self.total} [{percentage:>5.1f}%] {eta_str}')
        sys.stderr.flush()
        
        if self.current >= self.total:
            sys.stderr.write('\n')
            sys.stderr.flush()
    
    def close(self):
        """Finalize the progress bar"""
        if self.current < self.total:
            self.current = self.total
            self._render()


def detect_object_type_and_name(sql_content: str) -> Tuple[SQLObjectType, str]:
    """
    Detect SQL object type and extract its name from SQL content.
    
    Args:
        sql_content: The SQL file content
        
    Returns:
        Tuple of (object_type, object_name)
    """
    for obj_type, pattern in SQL_PATTERNS.items():
        match = pattern.search(sql_content)
        if match:
            try:
                name = match.group(1).strip('[]')
                return obj_type, name
            except (IndexError, AttributeError):
                return obj_type, "unknown"
    
    return SQLObjectType.UNKNOWN, "unknown"


def extract_columns(sql_content: str, obj_type: SQLObjectType) -> List[dict]:
    """
    Extract column definitions from CREATE TABLE statements.
    
    Args:
        sql_content: The SQL content
        obj_type: Type of SQL object
        
    Returns:
        List of column dictionaries
    """
    columns = []
    
    if obj_type != SQLObjectType.TABLE:
        return columns
    
    # Pattern to match column definitions
    column_pattern = re.compile(
        r'\[(\w+)\]\s+(\w+(?:\s*\([^)]+\))?)',
        re.IGNORECASE
    )
    
    matches = column_pattern.findall(sql_content)
    for col_name, col_type in matches[:50]:  # Limit to first 50 columns
        columns.append({
            "name": col_name,
            "type": col_type.strip()
        })
    
    return columns


def extract_parameters(sql_content: str, obj_type: SQLObjectType) -> List[dict]:
    """
    Extract parameters from stored procedures and functions.
    
    Args:
        sql_content: The SQL content
        obj_type: Type of SQL object
        
    Returns:
        List of parameter dictionaries
    """
    parameters = []
    
    if obj_type not in [SQLObjectType.PROCEDURE, SQLObjectType.FUNCTION]:
        return parameters
    
    # Pattern to match parameter definitions
    param_pattern = re.compile(
        r'@(\w+)\s+(\w+(?:\s*\([^)]+\))?)',
        re.IGNORECASE
    )
    
    matches = param_pattern.findall(sql_content)
    for param_name, param_type in matches[:20]:  # Limit to first 20 parameters
        parameters.append({
            "name": f"@{param_name}",
            "type": param_type.strip()
        })
    
    return parameters


def extract_dependencies(sql_content: str) -> List[str]:
    """
    Extract table/view dependencies from SQL content.
    
    Args:
        sql_content: The SQL content
        
    Returns:
        List of dependency names
    """
    dependencies = []
    
    # Pattern to match FROM, JOIN, and INTO clauses
    dep_pattern = re.compile(
        r'(?:FROM|JOIN|INTO)\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?',
        re.IGNORECASE
    )
    
    matches = dep_pattern.findall(sql_content)
    # Remove duplicates and limit
    dependencies = list(set(matches))[:20]
    
    return dependencies


def index_sql_repo(base_path: str, verbose: bool = True) -> Tuple[List[SQLObject], IndexStats]:
    """
    Index all SQL files in a repository with enhanced metadata extraction.
    
    Args:
        base_path: Root path to scan for SQL files
        verbose: Whether to show progress bars
        
    Returns:
        Tuple of (indexed_objects, statistics)
    """
    start_time = time.time()
    base = Path(base_path)
    
    if not base.exists():
        raise FileNotFoundError(f"Path does not exist: {base_path}")
    
    # Find all SQL files
    if verbose:
        sys.stderr.write(f"Scanning for SQL files in {base_path}...\n")
        sys.stderr.flush()
    
    sql_files = list(base.rglob("*.sql"))
    
    if verbose:
        sys.stderr.write(f"Found {len(sql_files)} SQL files\n")
        sys.stderr.flush()
    
    indexed_objects = []
    stats = IndexStats(total_files=len(sql_files))
    
    # Progress bar for indexing
    progress = ProgressBar(len(sql_files), desc="Indexing SQL files") if verbose else None
    
    for file_path in sql_files:
        try:
            # Read file with error handling
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            
            # Get file metadata
            file_stat = file_path.stat()
            file_size = file_stat.st_size
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)
            
            # Detect object type and name
            obj_type, obj_name = detect_object_type_and_name(content)
            
            # Extract additional metadata
            columns = extract_columns(content, obj_type)
            parameters = extract_parameters(content, obj_type)
            dependencies = extract_dependencies(content)
            
            # Create SQL object
            sql_obj = SQLObject(
                name=obj_name,
                type=obj_type,
                path=str(file_path),
                content=content,
                file_size=file_size,
                modified_at=modified_time,
                columns=columns,
                parameters=parameters,
                dependencies=dependencies
            )
            
            indexed_objects.append(sql_obj)
            stats.total_size_bytes += file_size
            
            # Update type-specific counters
            if obj_type == SQLObjectType.TABLE:
                stats.tables += 1
            elif obj_type == SQLObjectType.VIEW:
                stats.views += 1
            elif obj_type == SQLObjectType.PROCEDURE:
                stats.procedures += 1
            elif obj_type == SQLObjectType.FUNCTION:
                stats.functions += 1
            elif obj_type == SQLObjectType.TRIGGER:
                stats.triggers += 1
            else:
                stats.unknown += 1
            
        except Exception as e:
            stats.failed_files += 1
            if verbose:
                sys.stderr.write(f"\nWarning: Failed to index {file_path}: {str(e)}\n")
                sys.stderr.flush()
        
        if progress:
            progress.update(1)
    
    if progress:
        progress.close()
    
    stats.total_objects = len(indexed_objects)
    stats.index_time_seconds = time.time() - start_time
    
    if verbose:
        sys.stderr.write(f"\n✓ Indexing complete!\n")
        sys.stderr.write(f"  Total objects: {stats.total_objects}\n")
        sys.stderr.write(f"  Tables: {stats.tables}, Views: {stats.views}, ")
        sys.stderr.write(f"Procedures: {stats.procedures}, Functions: {stats.functions}\n")
        sys.stderr.write(f"  Time taken: {stats.index_time_seconds:.2f}s\n\n")
        sys.stderr.flush()
    
    return indexed_objects, stats


def search_objects(
    indexed_objects: List[SQLObject],
    query: str,
    limit: int = 20,
    object_types: Optional[List[SQLObjectType]] = None
) -> List[dict]:
    """
    Search indexed SQL objects with relevance scoring.
    
    Args:
        indexed_objects: List of indexed SQL objects
        query: Search query string
        limit: Maximum number of results
        object_types: Optional filter by object types
        
    Returns:
        List of search results sorted by relevance
    """
    query_lower = query.lower()
    query_terms = query_lower.split()
    results = []
    
    for obj in indexed_objects:
        # Filter by type if specified
        if object_types and obj.type not in object_types:
            continue
        
        # Calculate relevance score
        score = 0.0
        
        # Exact name match gets highest score
        if obj.name.lower() == query_lower:
            score += 100
        elif query_lower in obj.name.lower():
            score += 50
        
        # Check for query terms in name (weighted)
        for term in query_terms:
            if term in obj.name.lower():
                score += 20
        
        # Check for query in content
        if query_lower in obj.searchable_text:
            score += 10
            
        # Check for query terms in content
        for term in query_terms:
            if term in obj.searchable_text:
                score += 2
        
        # Add result if score > 0
        if score > 0:
            # Extract matched content snippet
            content_lower = obj.content.lower()
            match_idx = content_lower.find(query_lower)
            matched_snippet = None
            
            if match_idx != -1:
                start = max(0, match_idx - 50)
                end = min(len(obj.content), match_idx + 100)
                matched_snippet = obj.content[start:end].strip()
            
            results.append({
                "name": obj.name,
                "type": obj.type.value,
                "path": obj.path,
                "relevance_score": score,
                "line_count": obj.line_count,
                "matched_snippet": matched_snippet
            })
    
    # Sort by relevance score (descending)
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return results[:limit]