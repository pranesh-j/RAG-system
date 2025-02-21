import weaviate
from typing import List, Dict, Any, Optional
import uuid
from app.core.config import settings

class WeaviateService:
    def __init__(self):
        self.client = weaviate.Client(
            url=settings.WEAVIATE_URL,
        )
        self._setup_schema()

    def _setup_schema(self):
        """Setup Weaviate schema if it doesn't exist"""
        # Document chunk schema
        chunk_class = {
            "class": "DocumentChunk",
            "vectorizer": "none",  # We'll provide our own vectors
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "The text content of the document chunk",
                },
                {
                    "name": "documentId",
                    "dataType": ["string"],
                    "description": "ID of the parent document",
                },
                {
                    "name": "chunkIndex",
                    "dataType": ["int"],
                    "description": "Index of this chunk in the document",
                },
                {
                    "name": "fileType",
                    "dataType": ["string"],
                    "description": "Type of the source file",
                },
                {
                    "name": "metadata",
                    "dataType": ["text"],
                    "description": "Additional metadata as JSON string",
                }
            ]
        }

        # Create schema if it doesn't exist
        try:
            if not self.client.schema.exists("DocumentChunk"):
                self.client.schema.create_class(chunk_class)
        except Exception as e:
            print(f"Error setting up schema: {str(e)}")
            raise

    async def add_document_chunks(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        document_id: str,
        file_type: str,
        metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Add document chunks with their embeddings to Weaviate
        Returns list of chunk IDs
        """
        chunk_ids = []
        try:
            # Add each chunk with its embedding
            with self.client.batch as batch:
                for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_id = str(uuid.uuid4())
                    
                    properties = {
                        "content": chunk,
                        "documentId": document_id,
                        "chunkIndex": idx,
                        "fileType": file_type,
                        "metadata": str(metadata)  # Convert dict to string
                    }
                    
                    batch.add_data_object(
                        data_object=properties,
                        class_name="DocumentChunk",
                        uuid=chunk_id,
                        vector=embedding
                    )
                    chunk_ids.append(chunk_id)
                    
            return chunk_ids
        except Exception as e:
            print(f"Error adding document chunks: {str(e)}")
            raise

    async def delete_document(self, document_id: str):
        """Delete all chunks associated with a document"""
        try:
            where_filter = {
                "path": ["documentId"],
                "operator": "Equal",
                "valueString": document_id
            }
            
            self.client.batch.delete_objects(
                class_name="DocumentChunk",
                where=where_filter
            )
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
            raise

    async def query_document(
        self,
        query_embedding: List[float],
        document_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Query chunks from a specific document using vector similarity
        Returns the most relevant chunks
        """
        try:
            where_filter = {
                "path": ["documentId"],
                "operator": "Equal",
                "valueString": document_id
            }
            
            result = (
                self.client.query
                .get("DocumentChunk", ["content", "chunkIndex", "documentId", "metadata"])
                .with_where(where_filter)
                .with_near_vector({
                    "vector": query_embedding,
                    "certainty": 0.7
                })
                .with_limit(limit)
                .do()
            )
            
            return result.get("data", {}).get("Get", {}).get("DocumentChunk", [])
        except Exception as e:
            print(f"Error querying document: {str(e)}")
            raise

    async def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a document"""
        try:
            where_filter = {
                "path": ["documentId"],
                "operator": "Equal",
                "valueString": document_id
            }
            
            result = (
                self.client.query
                .get("DocumentChunk", ["metadata", "fileType"])
                .with_where(where_filter)
                .with_limit(1)
                .do()
            )
            
            chunks = result.get("data", {}).get("Get", {}).get("DocumentChunk", [])
            if chunks:
                return {
                    "fileType": chunks[0]["fileType"],
                    "metadata": eval(chunks[0]["metadata"])  # Convert string back to dict
                }
            return None
        except Exception as e:
            print(f"Error getting document metadata: {str(e)}")
            raise

# Create singleton instance
weaviate_service = WeaviateService()