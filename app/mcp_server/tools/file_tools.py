"""
MCP Tool implementations for file access.
DELEGATES TO: app.mcp_server.server.MCPServer

This module provides a simple interface that delegates to the full MCP server
implementation for actual file operations.
"""

from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Import the server
sys.path.insert(0, str(Path(__file__).parent.parent))
from server import MCPServer

# Singleton server instance
_server_instance: Optional[MCPServer] = None


def _get_server() -> MCPServer:
    """Get or create MCP server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = MCPServer()
    return _server_instance


def list_source_files(directory: Optional[str] = None) -> Dict[str, Any]:
    """List all available source files in seed_data.
    
    Args:
        directory: Optional subdirectory to list (relative to seed_data/)
        
    Returns:
        Dictionary with file list and metadata
    """
    return _get_server().list_source_files(directory)


def read_source_file(path: str) -> Dict[str, Any]:
    """Read content of a source file.
    
    Args:
        path: Relative path within seed_data/ (e.g., "source_code/billing_service.py")
        
    Returns:
        Dictionary with file content or error
    """
    return _get_server().read_source_file(path)


def get_template(template_name: str) -> Dict[str, Any]:
    """Get a document template.
    
    Args:
        template_name: Name of template ("technical-spec", "sop", "process-map")
        
    Returns:
        Dictionary with template content or error
    """
    return _get_server().get_template(template_name)


def get_source_metadata(path: str) -> Dict[str, Any]:
    """Get metadata for a source file.
    
    Args:
        path: Relative path within seed_data/
        
    Returns:
        Dictionary with metadata or error
    """
    return _get_server().get_source_metadata(path)


def log_tool_call(tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Log a tool call for audit purposes (delegated to server).
    
    Args:
        tool_name: Name of tool called
        parameters: Parameters passed to tool
        result: Result returned by tool
    """
    # The server handles logging internally
    pass
