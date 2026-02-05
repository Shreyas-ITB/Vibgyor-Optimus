from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SQLObjectType(Enum):
    """Enumeration of SQL object types"""
    TABLE = "table"
    VIEW = "view"
    PROCEDURE = "procedure"
    FUNCTION = "function"
    TRIGGER = "trigger"
    INDEX = "index"
    UNKNOWN = "unknown"


@dataclass
class SQLObject:
    """Represents a SQL database object with metadata"""
    name: str
    type: SQLObjectType
    path: str
    content: str
    
    # Additional metadata
    file_size: int = 0
    line_count: int = 0
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    
    # Extracted schema information
    columns: List[Dict[str, str]] = field(default_factory=list)
    parameters: List[Dict[str, str]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Search optimization
    searchable_text: str = field(default="", init=False)
    
    def __post_init__(self):
        """Generate searchable text after initialization"""
        self.searchable_text = f"{self.name} {self.type.value} {self.content}".lower()
        self.line_count = len(self.content.splitlines()) if self.content else 0


@dataclass
class IndexStats:
    """Statistics about the indexed database"""
    total_files: int = 0
    total_objects: int = 0
    tables: int = 0
    views: int = 0
    procedures: int = 0
    functions: int = 0
    triggers: int = 0
    unknown: int = 0
    failed_files: int = 0
    total_size_bytes: int = 0
    index_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "total_files": self.total_files,
            "total_objects": self.total_objects,
            "breakdown": {
                "tables": self.tables,
                "views": self.views,
                "procedures": self.procedures,
                "functions": self.functions,
                "triggers": self.triggers,
                "unknown": self.unknown,
            },
            "failed_files": self.failed_files,
            "total_size_mb": round(self.total_size_bytes / (1024 * 1024), 2),
            "index_time_seconds": round(self.index_time_seconds, 2)
        }


@dataclass
class SearchResult:
    """Represents a search result with relevance scoring"""
    sql_object: SQLObject
    relevance_score: float = 0.0
    matched_content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary"""
        return {
            "name": self.sql_object.name,
            "type": self.sql_object.type.value,
            "path": self.sql_object.path,
            "relevance_score": round(self.relevance_score, 2),
            "line_count": self.sql_object.line_count,
            "matched_content": self.matched_content
        }