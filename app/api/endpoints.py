from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query, Depends
from typing import List, Optional
import uuid
import logging

from app.services.document_processor import document_processor
from app.services.embeddings import embedding_service
from app.services.weaviate_service import weaviate_service
from app.utils.file_handler import file_handler
from .models import (
    DocumentResponse, 
    QueryRequest, 
    QueryResponse,
    DocumentListResponse,
    JsonAggregationRequest,
    JsonAggregationResponse,
    CrossDocumentQueryRequest,
    CrossDocumentQueryResponse
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

SUPPORTED_FORMATS = {'pdf', 'docx', 'txt', 'json'}

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
) -> DocumentResponse:
    """
    Upload and process a document
    
    This endpoint accepts document files in PDF, DOCX, TXT, or JSON format,
    processes them into chunks, generates embeddings, and stores them in Weaviate.
    
    Returns the document ID and metadata.
    """
    # Validate file format
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    try:
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        logger.info(f"Processing document upload: {file.filename} (ID: {document_id})")
        
        # Save file temporarily
        file_path, file_type = await file_handler.save_upload_file(file)
        
        # Process document
        doc_result = await document_processor.process_file(file_path, file_type)
        
        # Get embeddings for chunks
        logger.info(f"Generating embeddings for {len(doc_result['chunks'])} chunks")
        embeddings = await embedding_service.get_batch_embeddings(doc_result["chunks"])
        
        # Store in Weaviate
        logger.info(f"Storing document chunks in Weaviate")
        await weaviate_service.add_document_chunks(
            chunks=doc_result["chunks"],
            embeddings=embeddings,
            document_id=document_id,
            file_type=file_type,
            metadata=doc_result["metadata"],
            filename=file.filename
        )
        
        # Schedule cleanup
        background_tasks.add_task(file_handler.cleanup_file, file_path)
        
        logger.info(f"Document {document_id} processed successfully")
        
        return DocumentResponse(
            document_id=document_id,
            message="Document processed successfully",
            metadata=doc_result["metadata"]
        )
        
    except Exception as e:
        logger.error(f"Error processing document upload: {str(e)}")
        # Ensure cleanup happens even on error
        if 'file_path' in locals():
            background_tasks.add_task(file_handler.cleanup_file, file_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
) -> DocumentResponse:
    """
    Update an existing document
    
    This endpoint replaces an existing document with a new version.
    It deletes the old document and processes the new one with the same document ID.
    """
    # Validate file format
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )
        
    try:
        logger.info(f"Updating document: {document_id}")
        
        # Verify document exists
        metadata = await weaviate_service.get_document_metadata(document_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        # Delete existing document
        await weaviate_service.delete_document(document_id)
        
        # Process new document
        file_path, file_type = await file_handler.save_upload_file(file)
        
        # Process document
        doc_result = await document_processor.process_file(file_path, file_type)
        
        # Get embeddings for chunks
        embeddings = await embedding_service.get_batch_embeddings(doc_result["chunks"])
        
        # Store in Weaviate
        await weaviate_service.add_document_chunks(
            chunks=doc_result["chunks"],
            embeddings=embeddings,
            document_id=document_id,
            file_type=file_type,
            metadata=doc_result["metadata"],
            filename=file.filename
        )
        
        # Schedule cleanup
        background_tasks.add_task(file_handler.cleanup_file, file_path)
        
        logger.info(f"Document {document_id} updated successfully")
        
        return DocumentResponse(
            document_id=document_id,
            message="Document updated successfully",
            metadata=doc_result["metadata"]
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error updating document: {str(e)}")
        if 'file_path' in locals():
            background_tasks.add_task(file_handler.cleanup_file, file_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and all its chunks
    
    This endpoint completely removes a document and all associated data from the system.
    """
    try:
        logger.info(f"Deleting document: {document_id}")
        
        # Verify document exists
        metadata = await weaviate_service.get_document_metadata(document_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        # Delete document
        await weaviate_service.delete_document(document_id)
        
        logger.info(f"Document {document_id} deleted successfully")
        
        return {"message": f"Document {document_id} deleted successfully"}
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResponse)
async def query_document(query_request: QueryRequest) -> QueryResponse:
    """
    Query a document using semantic search
    
    This endpoint takes a natural language query and a document ID,
    and returns the most relevant chunks from that document.
    """
    try:
        logger.info(f"Processing query for document: {query_request.document_id}")
        
        # Get query embedding
        query_embedding = await embedding_service.get_embeddings(query_request.query)
        
        # Get metadata
        metadata = await weaviate_service.get_document_metadata(query_request.document_id)
        
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Document {query_request.document_id} not found"
            )
        
        # Perform query
        matches = await weaviate_service.query_document(
            query_embedding=query_embedding,
            document_id=query_request.document_id,
            limit=query_request.limit
        )
        
        logger.info(f"Query returned {len(matches)} matches")
        
        return QueryResponse(
            document_id=query_request.document_id,
            matches=matches,
            metadata=metadata
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cross-query", response_model=CrossDocumentQueryResponse)
async def cross_document_query(query_request: CrossDocumentQueryRequest) -> CrossDocumentQueryResponse:
    """
    Query across all documents
    
    This endpoint takes a natural language query and returns the most relevant chunks
    from all documents in the system. Optionally filter by file type.
    """
    try:
        logger.info(f"Processing cross-document query")
        
        # Get query embedding
        query_embedding = await embedding_service.get_embeddings(query_request.query)
        
        # Perform query
        matches = await weaviate_service.query_across_documents(
            query_embedding=query_embedding,
            limit=query_request.limit,
            file_type=query_request.file_type
        )
        
        logger.info(f"Cross-document query returned {len(matches)} matches")
        
        # Group by document
        documents = {}
        for match in matches:
            doc_id = match.get("documentId")
            if doc_id not in documents:
                documents[doc_id] = []
            documents[doc_id].append(match)
        
        # Format the response
        results = [
            {
                "document_id": doc_id,
                "matches": matches
            }
            for doc_id, matches in documents.items()
        ]
        
        return CrossDocumentQueryResponse(
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error processing cross-document query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """
    List all documents
    
    This endpoint returns a list of all documents in the system with their metadata.
    """
    try:
        logger.info("Retrieving document list")
        
        documents = await weaviate_service.list_documents()
        
        logger.info(f"Retrieved {len(documents)} documents")
        
        return DocumentListResponse(
            documents=documents
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}")
async def get_document_info(document_id: str):
    """
    Get document information
    
    This endpoint returns metadata for a specific document.
    """
    try:
        logger.info(f"Retrieving metadata for document: {document_id}")
        
        metadata = await weaviate_service.get_document_metadata(document_id)
        
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        logger.info(f"Retrieved metadata for document: {document_id}")
        
        return metadata
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error retrieving document metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/json-aggregation", response_model=JsonAggregationResponse)
async def json_aggregation(aggregation_request: JsonAggregationRequest) -> JsonAggregationResponse:
    """
    Perform aggregation on JSON document fields (BONUS FEATURE)
    
    This endpoint performs aggregation operations like min, max, sum, avg, count
    on numeric fields in JSON documents. Only works with JSON documents.
    
    Operations: min, max, sum, avg, count
    """
    try:
        logger.info(f"Processing JSON aggregation request for document: {aggregation_request.document_id}")
        
        # Verify document exists and is a JSON file
        metadata = await weaviate_service.get_document_metadata(aggregation_request.document_id)
        
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Document {aggregation_request.document_id} not found"
            )
        
        if metadata.get("fileType") != "json":
            raise HTTPException(
                status_code=400,
                detail=f"Document {aggregation_request.document_id} is not a JSON file"
            )
        
        # Perform aggregation
        result = await weaviate_service.json_aggregation_query(
            document_id=aggregation_request.document_id,
            field=aggregation_request.field,
            operation=aggregation_request.operation
        )
        
        logger.info(f"JSON aggregation completed successfully")
        
        return JsonAggregationResponse(
            document_id=aggregation_request.document_id,
            field=aggregation_request.field,
            operation=aggregation_request.operation,
            result=result["result"],
            source=result["source"]
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except ValueError as e:
        logger.error(f"Value error in JSON aggregation: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing JSON aggregation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))