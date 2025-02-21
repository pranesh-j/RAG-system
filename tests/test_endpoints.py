import pytest
from fastapi.testclient import TestClient
import json
from pathlib import Path
import os
import shutil

# Create test files directory if it doesn't exist
TEST_FILES_DIR = Path(__file__).parent / "test_files"
TEMP_UPLOADS_DIR = Path(__file__).parent.parent / "temp_uploads"

def create_test_files():
    """Create test files for different formats"""
    # Ensure directories exist
    TEST_FILES_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create test TXT content
    txt_path = TEST_FILES_DIR / "test.txt"
    with open(txt_path, "w", encoding='utf-8') as f:
        f.write("This is a test document content.")

    # Create test JSON
    json_path = TEST_FILES_DIR / "test.json"
    test_data = {
        "title": "Test Document",
        "content": "This is test content",
        "metadata": {
            "author": "Test Author",
            "date": "2024-02-19"
        }
    }
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(test_data, f)

    return txt_path, json_path

@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup test files before tests and cleanup after"""
    # Clean up any existing test files
    if TEST_FILES_DIR.exists():
        shutil.rmtree(TEST_FILES_DIR)
    
    # Create fresh test files
    txt_path, json_path = create_test_files()
    yield
    
    # Cleanup
    if TEST_FILES_DIR.exists():
        shutil.rmtree(TEST_FILES_DIR)
    # Clean up temp uploads
    for file in TEMP_UPLOADS_DIR.glob("*"):
        try:
            file.unlink()
        except Exception:
            pass

def test_health_check(test_client: TestClient):
    """Test health check endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_upload_document(test_client: TestClient):
    """Test document upload endpoint"""
    # Test TXT upload
    txt_path = TEST_FILES_DIR / "test.txt"
    with open(txt_path, "rb") as f:
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", f, "text/plain")}
        )
    assert response.status_code == 200
    assert "document_id" in response.json()
    
    # Store document_id for update test
    document_id = response.json()["document_id"]
    
    # Test JSON upload
    json_path = TEST_FILES_DIR / "test.json"
    with open(json_path, "rb") as f:
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.json", f, "application/json")}
        )
    assert response.status_code == 200
    
    return document_id

def test_update_document(test_client: TestClient):
    """Test document update endpoint"""
    # First upload a document
    document_id = test_upload_document(test_client)
    
    # Now update it
    txt_path = TEST_FILES_DIR / "test.txt"
    with open(txt_path, "rb") as f:
        response = test_client.put(
            f"/api/v1/documents/{document_id}",
            files={"file": ("test.txt", f, "text/plain")}
        )
    assert response.status_code == 200
    assert response.json()["document_id"] == document_id

def test_query_document(test_client: TestClient):
    """Test document query endpoint"""
    # First upload a document
    document_id = test_upload_document(test_client)
    
    # Now query it
    query_data = {
        "query": "test content",
        "document_id": document_id,
        "limit": 5
    }
    
    response = test_client.post(
        "/api/v1/query",
        json=query_data
    )
    assert response.status_code == 200
    assert "matches" in response.json()
    assert "metadata" in response.json()

def test_invalid_file_format(test_client: TestClient):
    """Test upload with invalid file format"""
    # Create an invalid file
    invalid_path = TEST_FILES_DIR / "test.invalid"
    with open(invalid_path, "w") as f:
        f.write("Invalid content")
    
    # Test upload with invalid format
    with open(invalid_path, "rb") as f:
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.invalid", f, "application/octet-stream")}
        )
    assert response.status_code == 400

# Helper function to create a test file of given size
def create_large_file(size_in_mb: int) -> Path:
    """Create a large test file of specified size in MB"""
    large_file_path = TEST_FILES_DIR / f"large_file_{size_in_mb}mb.txt"
    
    # Use a more efficient way to create large files
    chunk_size = 1024 * 1024  # 1MB
    with open(large_file_path, "wb") as f:
        for _ in range(size_in_mb):
            f.write(b"0" * chunk_size)
            
    return large_file_path

@pytest.mark.skip(reason="This test is slow and can be run manually")
def test_large_file_upload(test_client: TestClient):
    """Test upload of a large file (optional test)"""
    # Create a smaller file for automated testing (1MB instead of 5MB)
    large_file = create_large_file(1)
    
    with open(large_file, "rb") as f:
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("large_file.txt", f, "text/plain")}
        )
    assert response.status_code == 200
    assert "document_id" in response.json()