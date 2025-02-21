from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

class DocumentResponse(BaseModel):
    """Response model for document upload/update operations"""
    document_id: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    """Request model for document query"""
    query: str
    document_id: str
    limit: Optional[int] = Field(5, ge=1, le=20)

class QueryResponse(BaseModel):
    """Response model for document query"""
    document_id: str
    matches: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None

class DocumentListResponse(BaseModel):
    """Response model for listing documents"""
    documents: List[Dict[str, Any]]

class CrossDocumentQueryRequest(BaseModel):
    """Request model for cross-document query"""
    query: str
    limit: Optional[int] = Field(5, ge=1, le=20)
    file_type: Optional[str] = None  # Optional filter by file type

class DocumentQueryResult(BaseModel):
    """Result for a single document in cross-document query"""
    document_id: str
    matches: List[Dict[str, Any]]

class CrossDocumentQueryResponse(BaseModel):
    """Response model for cross-document query"""
    results: List[Dict[str, Any]]

class JsonAggregationRequest(BaseModel):
    """Request model for JSON aggregation operations (BONUS FEATURE)"""
    document_id: str
    field: str
    operation: str = Field(..., description="Operation: min, max, sum, avg, count")
    
    class Config:
        """Add validation for operation field"""
        @staticmethod
        def schema_extra(schema: Dict[str, Any], model) -> None:
            schema["properties"]["operation"]["enum"] = ["min", "max", "sum", "avg", "count"]

class JsonAggregationResponse(BaseModel):
    """Response model for JSON aggregation operations (BONUS FEATURE)"""
    document_id: str
    field: str
    operation: str
    result: Union[int, float, None]
    source: str = Field(..., description="Source of the result: precomputed or computed")