"""
Unit tests for MCP Server tools.
Tests path validation, security, file operations, and error handling.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path

# We need to import from the server module directly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "mcp_server"))

from server import MCPServer


class TestMCPServerInitialization:
    """Test MCP Server initialization."""
    
    def test_default_seed_data_path(self):
        """Test that server initializes with default path."""
        server = MCPServer()
        assert server.seed_data_path.exists()
        assert "seed_data" in str(server.seed_data_path)
    
    def test_custom_seed_data_path(self):
        """Test that server accepts custom seed data path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server = MCPServer(seed_data_path=tmpdir)
            assert str(server.seed_data_path) == str(Path(tmpdir).resolve())
    
    def test_supported_extensions(self):
        """Test that server has correct supported extensions."""
        server = MCPServer()
        assert '.py' in server.supported_extensions
        assert '.md' in server.supported_extensions
        assert '.yaml' in server.supported_extensions
        assert '.exe' not in server.supported_extensions


class TestPathValidation:
    """Test path validation and security controls."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for tests."""
        return MCPServer()
    
    def test_valid_relative_path(self, server):
        """Test that valid relative paths are accepted."""
        is_valid, error, resolved = server._validate_path("source_code/test.py")
        assert is_valid is True
        assert error is None
        assert resolved is not None
        assert "seed_data" in str(resolved)
    
    def test_directory_traversal_blocked(self, server):
        """Test that directory traversal is blocked."""
        is_valid, error, resolved = server._validate_path("../etc/passwd")
        assert is_valid is False
        assert error is not None
        assert "traversal" in error.lower()
    
    def test_absolute_path_blocked(self, server):
        """Test that absolute paths are blocked."""
        is_valid, error, resolved = server._validate_path("/etc/passwd")
        assert is_valid is False
        assert error is not None
        assert "absolute" in error.lower()
    
    def test_empty_path_blocked(self, server):
        """Test that empty paths are blocked."""
        is_valid, error, resolved = server._validate_path("")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_unsupported_extension_blocked(self, server):
        """Test that unsupported file types are blocked."""
        is_valid, error, resolved = server._validate_path("test.exe")
        assert is_valid is False
        assert "not supported" in error.lower()
    
    def test_path_outside_seed_data_blocked(self, server):
        """Test that paths outside seed_data are blocked (via symlink check)."""
        # This tests the resolve() and relative_to() check
        is_valid, error, resolved = server._validate_path("source_code/../../../etc/passwd")
        assert is_valid is False
        assert error is not None


class TestListSourceFiles:
    """Test list_source_files tool."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for tests."""
        return MCPServer()
    
    def test_list_all_files(self, server):
        """Test listing all files in seed_data."""
        result = server.list_source_files()
        
        assert result["success"] is True
        assert "files" in result
        assert result["count"] > 0
        
        # Check that expected files are present
        files = result["files"]
        assert any("billing_service.py" in f for f in files)
        assert any("billing_requirements.md" in f for f in files)
    
    def test_list_specific_directory(self, server):
        """Test listing files in a specific directory."""
        result = server.list_source_files("source_code")
        
        assert result["success"] is True
        assert result["directory"] == "source_code"
        
        # Should only have Python files
        for file in result["files"]:
            assert file.endswith(".py")
    
    def test_list_invalid_directory(self, server):
        """Test listing non-existent directory."""
        result = server.list_source_files("nonexistent")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_list_traversal_blocked(self, server):
        """Test that directory traversal is blocked."""
        result = server.list_source_files("../")
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_PATH"


class TestReadSourceFile:
    """Test read_source_file tool."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for tests."""
        return MCPServer()
    
    def test_read_existing_file(self, server):
        """Test reading an existing file."""
        result = server.read_source_file("source_code/billing_service.py")
        
        assert result["success"] is True
        assert "content" in result
        assert "size" in result
        assert "BillingService" in result["content"]
    
    def test_read_nonexistent_file(self, server):
        """Test reading a file that doesn't exist."""
        result = server.read_source_file("nonexistent/file.py")
        
        assert result["success"] is False
        assert result["error"]["code"] == "FILE_NOT_FOUND"
    
    def test_read_traversal_blocked(self, server):
        """Test that path traversal is blocked."""
        result = server.read_source_file("../etc/passwd")
        
        assert result["success"] is False
        assert result["error"]["code"] == "PATH_VALIDATION_ERROR"
    
    def test_read_unsupported_type(self, server):
        """Test that unsupported file types are rejected."""
        result = server.read_source_file("test.exe")
        
        assert result["success"] is False
        assert result["error"]["code"] == "PATH_VALIDATION_ERROR"
    
    def test_read_requires_md(self, server):
        """Test reading requirements document."""
        result = server.read_source_file("specifications/billing_requirements.md")
        
        assert result["success"] is True
        assert "Billing Service Requirements" in result["content"]
        assert "OUTDATED" in result["content"]  # Known issue marker
    
    def test_read_meeting_notes(self, server):
        """Test reading meeting notes."""
        result = server.read_source_file("meeting_notes/billing-system-review.md")
        
        assert result["success"] is True
        assert "DEC-001" in result["content"]
        assert "$10,000" in result["content"]  # Decision threshold


class TestGetTemplate:
    """Test get_template tool."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for tests."""
        return MCPServer()
    
    def test_get_technical_spec_template(self, server):
        """Test getting technical spec template."""
        result = server.get_template("technical-spec")
        
        assert result["success"] is True
        assert "Technical Specification" in result["content"]
        assert "placeholders" in result
    
    def test_get_sop_template(self, server):
        """Test getting SOP template."""
        result = server.get_template("sop")
        
        assert result["success"] is True
        assert "Standard Operating Procedure" in result["content"]
    
    def test_get_process_map_template(self, server):
        """Test getting process map template."""
        result = server.get_template("process-map")
        
        assert result["success"] is True
        assert "Process Map" in result["content"]
    
    def test_get_template_underscore_format(self, server):
        """Test that underscore format also works."""
        result1 = server.get_template("technical-spec")
        result2 = server.get_template("technical_spec")
        
        assert result1["success"] is True
        assert result2["success"] is True
    
    def test_get_invalid_template(self, server):
        """Test getting non-existent template."""
        result = server.get_template("invalid-template")
        
        assert result["success"] is False
        assert result["error"]["code"] == "TEMPLATE_NOT_FOUND"


class TestGetSourceMetadata:
    """Test get_source_metadata tool."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for tests."""
        return MCPServer()
    
    def test_get_python_file_metadata(self, server):
        """Test getting metadata for Python file."""
        result = server.get_source_metadata("source_code/billing_service.py")
        
        assert result["success"] is True
        assert result["classification"]["doc_type"] == "source_code"
        assert "file_info" in result
        assert "size" in result["file_info"]
    
    def test_get_requirements_metadata(self, server):
        """Test getting metadata for requirements file."""
        result = server.get_source_metadata("specifications/billing_requirements.md")
        
        assert result["success"] is True
        assert result["classification"]["doc_type"] == "requirements"
        # Should have known issues from metadata
        assert "known_issues" in result
    
    def test_get_meeting_notes_metadata(self, server):
        """Test getting metadata for meeting notes."""
        result = server.get_source_metadata("meeting_notes/billing-system-review.md")
        
        assert result["success"] is True
        assert result["classification"]["doc_type"] == "meeting_notes"
    
    def test_get_metadata_nonexistent_file(self, server):
        """Test getting metadata for non-existent file."""
        result = server.get_source_metadata("nonexistent/file.py")
        
        assert result["success"] is False
        assert result["error"]["code"] == "FILE_NOT_FOUND"
    
    def test_get_metadata_traversal_blocked(self, server):
        """Test that path traversal is blocked."""
        result = server.get_source_metadata("../etc/passwd")
        
        assert result["success"] is False
        assert result["error"]["code"] == "PATH_VALIDATION_ERROR"


class TestIntegration:
    """Integration tests combining multiple tools."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for tests."""
        return MCPServer()
    
    def test_full_workflow_simulation(self, server):
        """Simulate a complete workflow using multiple tools."""
        # 1. List files
        list_result = server.list_source_files()
        assert list_result["success"] is True
        
        # 2. Get metadata for a file
        metadata_result = server.get_source_metadata("source_code/billing_service.py")
        assert metadata_result["success"] is True
        
        # 3. Read the file
        content_result = server.read_source_file("source_code/billing_service.py")
        assert content_result["success"] is True
        
        # 4. Get template
        template_result = server.get_template("technical-spec")
        assert template_result["success"] is True
        
        # All operations should have succeeded
        assert all([
            list_result["success"],
            metadata_result["success"],
            content_result["success"],
            template_result["success"]
        ])
    
    def test_metadata_matches_classification_yaml(self, server):
        """Test that metadata matches the classification.yaml file."""
        # Read a file that should have known issues
        result = server.get_source_metadata("specifications/billing_requirements.md")
        
        assert result["success"] is True
        assert len(result["known_issues"]) > 0
        
        # Check for expected known issues
        issues_text = str(result["known_issues"])
        assert any(keyword in issues_text for keyword in ["OUTDATED", "AMBIGUOUS", "MISSING"])


class TestSecurityEdgeCases:
    """Test security edge cases."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for tests."""
        return MCPServer()
    
    def test_null_byte_injection_blocked(self, server):
        """Test that null byte injection is blocked."""
        result = server.read_source_file("source_code/test.py\x00.txt")
        # Should fail validation due to invalid characters or not being a supported extension
        assert result["success"] is False
    
    def test_unicode_traversal_attempt(self, server):
        """Test unicode-based traversal attempts."""
        # Try various unicode encodings of ..
        attempts = [
            "source_code/..%2f..%2fetc/passwd",
            "source_code/%2e%2e/%2e%2e/etc/passwd",
        ]
        
        for attempt in attempts:
            result = server.read_source_file(attempt)
            assert result["success"] is False, f"Should have blocked: {attempt}"
    
    def test_case_sensitivity(self, server):
        """Test case handling."""
        # Extensions should be case-insensitive
        # Create a temp file with uppercase extension for testing
        with tempfile.NamedTemporaryFile(suffix='.PY', delete=False, dir=server.seed_data_path / "source_code") as f:
            f.write(b"# Test")
            temp_path = f.name
        
        try:
            result = server.read_source_file("source_code/" + Path(temp_path).name)
            # Should succeed (lowercase extension)
            assert result["success"] is True
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
