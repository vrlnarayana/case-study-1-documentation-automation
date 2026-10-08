#!/usr/bin/env python3
"""
MCP Server for Documentation Automation System.

Provides controlled access to domain resources (files, templates, metadata)
through the Model Context Protocol. Agents NEVER access files directly - 
all access goes through this server.

Security:
- Only seed_data/ directory is exposed
- Path validation prevents directory traversal
- All file types validated
- All calls logged for audit
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('mcp_server')


class MCPServer:
    """MCP Server implementation for Documentation Automation."""
    
    def __init__(self, seed_data_path: Optional[str] = None):
        """Initialize MCP Server.
        
        Args:
            seed_data_path: Path to seed_data directory. If None, uses default.
        """
        if seed_data_path:
            self.seed_data_path = Path(seed_data_path).resolve()
        else:
            # Default: seed_data/ in project root
            self.seed_data_path = Path(__file__).parent.parent.parent / "seed_data"
        
        logger.info(f"MCP Server initialized with seed_data: {self.seed_data_path}")
        
        # Supported file extensions
        self.supported_extensions = {'.py', '.md', '.yaml', '.yml', '.json', '.txt'}
        
        # Maximum file size (10MB)
        self.max_file_size = 10 * 1024 * 1024
        
        # Load metadata cache
        self._metadata_cache: Optional[Dict] = None
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """Load source classification metadata."""
        metadata_path = self.seed_data_path / "metadata" / "source-classification.yaml"
        if metadata_path.exists():
            try:
                import yaml
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self._metadata_cache = yaml.safe_load(f)
                logger.info("Loaded metadata cache")
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
                self._metadata_cache = {}
        else:
            self._metadata_cache = {}
    
    def _validate_path(self, relative_path: str) -> tuple[bool, Optional[str], Optional[Path]]:
        """Validate a file path for security.
        
        Rules:
        - Path must be relative (no leading /)
        - No directory traversal (../)
        - Must be within seed_data/
        - File extension must be supported
        
        Args:
            relative_path: Relative path from seed_data/
            
        Returns:
            Tuple of (is_valid, error_message, resolved_path)
        """
        # Check for empty path
        if not relative_path or not relative_path.strip():
            return False, "Path cannot be empty", None
        
        path_str = relative_path.strip()
        
        # Check for directory traversal
        if '..' in path_str:
            logger.warning(f"Path traversal attempt blocked: {path_str}")
            return False, "Directory traversal not allowed", None
        
        # Check for absolute paths
        if path_str.startswith('/') or path_str.startswith('\\'):
            logger.warning(f"Absolute path blocked: {path_str}")
            return False, "Absolute paths not allowed", None
        
        # Resolve to absolute path
        try:
            # Remove any ./ prefix and seed_data/ prefix if present
            clean_path = path_str
            if clean_path.startswith('./'):
                clean_path = clean_path[2:]
            if clean_path.startswith('seed_data/'):
                clean_path = clean_path[10:]
            
            full_path = (self.seed_data_path / clean_path).resolve()
            
            # Verify it's within seed_data (prevent symlink attacks)
            try:
                full_path.relative_to(self.seed_data_path)
            except ValueError:
                logger.warning(f"Path outside seed_data blocked: {path_str}")
                return False, "Path must be within seed_data/", None
            
        except Exception as e:
            logger.error(f"Path resolution error: {e}")
            return False, f"Invalid path: {e}", None
        
        # Check file extension (if it looks like a file)
        if '.' in Path(path_str).name:
            ext = Path(path_str).suffix.lower()
            if ext not in self.supported_extensions:
                logger.warning(f"Unsupported file type blocked: {ext}")
                return False, f"File type '{ext}' not supported. Supported: {', '.join(self.supported_extensions)}", None
        
        return True, None, full_path
    
    def _log_tool_call(self, tool_name: str, parameters: Dict, result: Dict) -> None:
        """Log a tool call for audit purposes.
        
        Args:
            tool_name: Name of tool called
            parameters: Parameters passed to tool
            result: Result returned by tool
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "parameters": parameters,
            "success": result.get("success", False),
            "error": result.get("error", {}).get("code") if not result.get("success") else None
        }
        logger.info(f"TOOL_CALL: {json.dumps(log_entry)}")
    
    def list_source_files(self, directory: Optional[str] = None) -> Dict[str, Any]:
        """List all available source files in seed_data.
        
        Args:
            directory: Optional subdirectory to list (relative to seed_data/)
            
        Returns:
            Dictionary with file list and metadata
        """
        parameters = {"directory": directory}
        
        try:
            if directory:
                is_valid, error_msg, base_path = self._validate_path(directory)
                if not is_valid:
                    result = {
                        "success": False,
                        "error": {"code": "INVALID_PATH", "message": error_msg}
                    }
                    self._log_tool_call("list_source_files", parameters, result)
                    return result
            else:
                base_path = self.seed_data_path
            
            if not base_path.exists():
                result = {
                    "success": False,
                    "error": {
                        "code": "DIRECTORY_NOT_FOUND",
                        "message": f"Directory not found: {directory}"
                    }
                }
                self._log_tool_call("list_source_files", parameters, result)
                return result
            
            # Recursively list all files
            files = []
            for item in base_path.rglob('*'):
                if item.is_file():
                    # Check if supported type
                    if item.suffix.lower() in self.supported_extensions:
                        # Get relative path from seed_data
                        rel_path = item.relative_to(self.seed_data_path)
                        files.append(str(rel_path))
            
            files.sort()
            
            result = {
                "success": True,
                "files": files,
                "count": len(files),
                "base_directory": str(self.seed_data_path),
                "directory": directory or "root"
            }
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            result = {
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
        
        self._log_tool_call("list_source_files", parameters, result)
        return result
    
    def read_source_file(self, path: str) -> Dict[str, Any]:
        """Read content of a source file.
        
        Args:
            path: Relative path within seed_data/ (e.g., "source_code/billing_service.py")
            
        Returns:
            Dictionary with file content or error
        """
        parameters = {"path": path}
        
        # Validate path
        is_valid, error_msg, full_path = self._validate_path(path)
        if not is_valid:
            result = {
                "success": False,
                "error": {"code": "PATH_VALIDATION_ERROR", "message": error_msg}
            }
            self._log_tool_call("read_source_file", parameters, result)
            return result
        
        try:
            # Check if file exists
            if not full_path.exists():
                result = {
                    "success": False,
                    "error": {
                        "code": "FILE_NOT_FOUND",
                        "message": f"File not found: {path}"
                    }
                }
                self._log_tool_call("read_source_file", parameters, result)
                return result
            
            # Check if it's a file (not directory)
            if not full_path.is_file():
                result = {
                    "success": False,
                    "error": {
                        "code": "NOT_A_FILE",
                        "message": f"Path is not a file: {path}"
                    }
                }
                self._log_tool_call("read_source_file", parameters, result)
                return result
            
            # Check file size
            file_size = full_path.stat().st_size
            if file_size > self.max_file_size:
                result = {
                    "success": False,
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": f"File size {file_size} exceeds maximum {self.max_file_size}"
                    }
                }
                self._log_tool_call("read_source_file", parameters, result)
                return result
            
            # Read file content
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with different encoding
                with open(full_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            
            result = {
                "success": True,
                "path": path,
                "content": content,
                "size": file_size,
                "encoding": "utf-8",
                "modified": datetime.fromtimestamp(full_path.stat().st_mtime).isoformat()
            }
            
        except PermissionError:
            logger.error(f"Permission denied reading: {path}")
            result = {
                "success": False,
                "error": {"code": "PERMISSION_DENIED", "message": f"Permission denied: {path}"}
            }
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            result = {
                "success": False,
                "error": {"code": "READ_ERROR", "message": f"Error reading file: {str(e)}"}
            }
        
        self._log_tool_call("read_source_file", parameters, result)
        return result
    
    def get_template(self, template_name: str) -> Dict[str, Any]:
        """Get a document template.
        
        Args:
            template_name: Name of template ("technical-spec", "sop", "process-map")
            
        Returns:
            Dictionary with template content or error
        """
        parameters = {"template_name": template_name}
        
        # Normalize template name
        normalized = template_name.lower().replace('_', '-')
        
        # Map to file names
        template_files = {
            "technical-spec": "technical-spec-template.md",
            "sop": "sop-template.md",
            "process-map": "process-map-template.md"
        }
        
        if normalized not in template_files:
            result = {
                "success": False,
                "error": {
                    "code": "TEMPLATE_NOT_FOUND",
                    "message": f"Template '{template_name}' not found",
                    "details": f"Available templates: {', '.join(template_files.keys())}"
                }
            }
            self._log_tool_call("get_template", parameters, result)
            return result
        
        # Read template file
        template_path = f"templates/{template_files[normalized]}"
        result = self.read_source_file(template_path)
        
        if result.get("success"):
            result["template_name"] = normalized
            # Extract placeholders from content
            import re
            placeholders = re.findall(r'\{\{(\w+)\}\}', result["content"])
            result["placeholders"] = list(set(placeholders))
        
        self._log_tool_call("get_template", parameters, result)
        return result
    
    def get_source_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata for a source file.
        
        Args:
            path: Relative path within seed_data/
            
        Returns:
            Dictionary with metadata or error
        """
        parameters = {"path": path}
        
        # Validate path
        is_valid, error_msg, full_path = self._validate_path(path)
        if not is_valid:
            result = {
                "success": False,
                "error": {"code": "PATH_VALIDATION_ERROR", "message": error_msg}
            }
            self._log_tool_call("get_source_metadata", parameters, result)
            return result
        
        try:
            # Get file info
            if not full_path.exists():
                result = {
                    "success": False,
                    "error": {"code": "FILE_NOT_FOUND", "message": f"File not found: {path}"}
                }
                self._log_tool_call("get_source_metadata", parameters, result)
                return result
            
            stat = full_path.stat()
            
            # Determine doc type from path
            doc_types = {
                "source_code/": "source_code",
                "specifications/": "requirements",
                "meeting_notes/": "meeting_notes",
                "existing_docs/": "existing_doc",
                "templates/": "template",
                "metadata/": "metadata",
            }
            
            doc_type = "unknown"
            for prefix, dtype in doc_types.items():
                if path.startswith(prefix):
                    doc_type = dtype
                    break
            
            # Try to get classification from metadata cache
            classification = {"doc_type": doc_type, "sensitivity": "internal", "classification": "standard"}
            known_issues = []
            
            if self._metadata_cache and "files" in self._metadata_cache:
                file_meta = self._metadata_cache["files"].get(path)
                if file_meta:
                    if isinstance(file_meta, dict):
                        if "classification" in file_meta and isinstance(file_meta["classification"], dict):
                            classification.update(file_meta["classification"])
                        if "known_issues" in file_meta and isinstance(file_meta["known_issues"], list):
                            known_issues = file_meta["known_issues"]
            
            result = {
                "success": True,
                "path": path,
                "classification": classification,
                "file_info": {
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": full_path.suffix.lower()
                },
                "known_issues": known_issues,
                "source_references": []
            }
            
        except Exception as e:
            logger.error(f"Error getting metadata for {path}: {e}")
            result = {
                "success": False,
                "error": {"code": "METADATA_ERROR", "message": str(e)}
            }
        
        self._log_tool_call("get_source_metadata", parameters, result)
        return result


# ============== CLI Interface ==============

def main():
    """Run MCP Server in stdio mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Server for Documentation Automation")
    parser.add_argument(
        "--seed-data",
        help="Path to seed_data directory",
        default=None
    )
    args = parser.parse_args()
    
    server = MCPServer(seed_data_path=args.seed_data)
    
    logger.info("MCP Server started (stdio mode)")
    
    # Simple stdio loop for MCP protocol
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            # Parse JSON-RPC request
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
                print(json.dumps(response), flush=True)
                continue
            
            method = request.get("method")
            params = request.get("params", {})
            req_id = request.get("id")
            
            # Route to appropriate handler
            if method == "list_source_files":
                result = server.list_source_files(params.get("directory"))
            elif method == "read_source_file":
                result = server.read_source_file(params.get("path"))
            elif method == "get_template":
                result = server.get_template(params.get("template_name"))
            elif method == "get_source_metadata":
                result = server.get_source_metadata(params.get("path"))
            else:
                result = {"success": False, "error": {"code": "METHOD_NOT_FOUND", "message": f"Method not found: {method}"}}
            
            # Send response
            response = {"jsonrpc": "2.0", "result": result, "id": req_id}
            print(json.dumps(response), flush=True)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None}
            print(json.dumps(response), flush=True)
    
    logger.info("MCP Server stopped")


if __name__ == "__main__":
    main()
