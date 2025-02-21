import pytest
import asyncio
from app.services.embeddings import embedding_service
from app.services.document_processor import document_processor
from app.services.weaviate_service import weaviate_service
from pathlib import Path
import shutil

TEST_FILES_DIR = Path(__file__).parent / "test_files"

@pytest.fixture(autouse=True)
def setup_test_dir():
    """Create and cleanup test directory"""
    TEST_FILES_DIR.mkdir(parents=True, exist_ok=True)
    yield
    if TEST_FILES_DIR.exists():
        shutil.rmtree(TEST_FILES_DIR)

@pytest.mark.asyncio
async def test_embedding_service():
    """Test embedding generation"""
    test_text = "This is a test document"
    embedding = await embedding_service.get_embeddings(test_text)
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)

@pytest.mark.asyncio
async def test_document_processor():
    """Test document processing"""
    # Create a test text file
    test_file = TEST_FILES_DIR / "test.txt"
    test_content = "This is a test document.\nIt has multiple lines.\nEach line should be processed."
    
    test_file.write_text(test_content)
    
    result = await document_processor.process_file(str(test_file), "txt")
    assert "chunks" in result
    assert "metadata" in result
    assert len(result["chunks"]) > 0

@pytest.mark.asyncio
async def test_weaviate_service():
    """Test Weaviate operations"""
    document_id = "test-doc-id"
    chunks = ["This is chunk 1", "This is chunk 2"]
    embeddings = await embedding_service.get_batch_embeddings(chunks)
    
    # Test adding chunks
    chunk_ids = await weaviate_service.add_document_chunks(
        chunks=chunks,
        embeddings=embeddings,
        document_id=document_id,
        file_type="txt",
        metadata={"test": "metadata"}
    )
    assert len(chunk_ids) == len(chunks)
    
    # Test querying
    query_embedding = await embedding_service.get_embeddings("chunk 1")
    results = await weaviate_service.query_document(
        query_embedding=query_embedding,
        document_id=document_id
    )
    assert len(results) > 0
    
    # Test deletion
    await weaviate_service.delete_document(document_id)
    
    # Verify deletion
    metadata = await weaviate_service.get_document_metadata(document_id)
    assert metadata is None