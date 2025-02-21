import json
from typing import List, Dict, Any
import fitz  # PyMuPDF
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import settings
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True,
        )

    async def process_pdf(self, file_path: str) -> List[str]:
        """Process PDF files and return chunks of text"""
        try:
            logger.info(f"Processing PDF: {file_path}")
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            chunks = self.text_splitter.split_text(text)
            logger.info(f"PDF processed into {len(chunks)} chunks")
            
            # Limit number of chunks if it exceeds max
            if len(chunks) > settings.MAX_CHUNKS_PER_DOC:
                logger.warning(f"Limiting chunks from {len(chunks)} to {settings.MAX_CHUNKS_PER_DOC}")
                chunks = chunks[:settings.MAX_CHUNKS_PER_DOC]
                
            return chunks
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

    async def process_docx(self, file_path: str) -> List[str]:
        """Process DOCX files and return chunks of text"""
        try:
            logger.info(f"Processing DOCX: {file_path}")
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            chunks = self.text_splitter.split_text(text)
            logger.info(f"DOCX processed into {len(chunks)} chunks")
            
            # Limit number of chunks if it exceeds max
            if len(chunks) > settings.MAX_CHUNKS_PER_DOC:
                logger.warning(f"Limiting chunks from {len(chunks)} to {settings.MAX_CHUNKS_PER_DOC}")
                chunks = chunks[:settings.MAX_CHUNKS_PER_DOC]
                
            return chunks
        except Exception as e:
            logger.error(f"Error processing DOCX: {str(e)}")
            raise

    async def process_txt(self, file_path: str) -> List[str]:
        """Process TXT files and return chunks of text"""
        try:
            logger.info(f"Processing TXT: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                text = file.read()
            chunks = self.text_splitter.split_text(text)
            logger.info(f"TXT processed into {len(chunks)} chunks")
            
            # Limit number of chunks if it exceeds max
            if len(chunks) > settings.MAX_CHUNKS_PER_DOC:
                logger.warning(f"Limiting chunks from {len(chunks)} to {settings.MAX_CHUNKS_PER_DOC}")
                chunks = chunks[:settings.MAX_CHUNKS_PER_DOC]
                
            return chunks
        except Exception as e:
            logger.error(f"Error processing TXT: {str(e)}")
            raise

    async def process_json(self, file_path: str) -> Dict[str, Any]:
        """
        Process JSON files and return both structured and text representation
        Returns both the original structure and text chunks for embedding
        """
        try:
            logger.info(f"Processing JSON: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            # Convert to string for text embedding
            text_content = json.dumps(data, indent=2)
            chunks = self.text_splitter.split_text(text_content)
            logger.info(f"JSON processed into {len(chunks)} chunks")
            
            # Limit number of chunks if it exceeds max
            if len(chunks) > settings.MAX_CHUNKS_PER_DOC:
                logger.warning(f"Limiting chunks from {len(chunks)} to {settings.MAX_CHUNKS_PER_DOC}")
                chunks = chunks[:settings.MAX_CHUNKS_PER_DOC]
            
            # Extract structured metadata for the bonus part
            aggregation_metadata = self._extract_json_metadata(data)
            
            return {
                "structured_data": data,
                "text_chunks": chunks,
                "aggregation_metadata": aggregation_metadata
            }
        except Exception as e:
            logger.error(f"Error processing JSON: {str(e)}")
            raise

    def _extract_json_metadata(self, data: Any) -> Dict[str, Any]:
        """
        Extract useful metadata from JSON for the bonus query capabilities
        This helps with structured queries like max, min, avg, etc.
        """
        metadata = {}
        
        # If the JSON is a list of dictionaries
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            # Get all keys from the first item
            if data:
                # Keep track of numeric fields for potential aggregations
                numeric_fields = {}
                
                # For each field in the first object, see if it's consistent across all objects
                for key in data[0].keys():
                    # Check if the field exists in all items and is numeric
                    is_numeric = all(
                        isinstance(item.get(key), (int, float)) 
                        for item in data if key in item
                    )
                    
                    if is_numeric:
                        # Store min, max, sum, avg for each numeric field
                        values = [item[key] for item in data if key in item]
                        numeric_fields[key] = {
                            "min": min(values) if values else None,
                            "max": max(values) if values else None,
                            "sum": sum(values) if values else None,
                            "avg": sum(values) / len(values) if values else None,
                            "count": len(values)
                        }
                
                metadata["numeric_fields"] = numeric_fields
                
                # Track categories/enumerations for categorical fields
                categorical_fields = {}
                for key in data[0].keys():
                    # Check if field appears to be categorical (string with repeating values)
                    if all(isinstance(item.get(key), str) for item in data if key in item):
                        # Count occurrences of each value
                        value_counts = {}
                        for item in data:
                            if key in item:
                                value = item[key]
                                value_counts[value] = value_counts.get(value, 0) + 1
                        
                        # Only consider fields with reasonable number of categories
                        if len(value_counts) <= 50:  # Arbitrary threshold
                            categorical_fields[key] = value_counts
                
                metadata["categorical_fields"] = categorical_fields
                
        return metadata

    async def process_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Main method to process any supported file type
        Returns both chunks and metadata
        """
        processors = {
            'pdf': self.process_pdf,
            'docx': self.process_docx,
            'txt': self.process_txt,
            'json': self.process_json
        }
        
        if file_type not in processors:
            raise ValueError(f"Unsupported file type: {file_type}")
            
        try:
            if file_type == 'json':
                result = await processors[file_type](file_path)
                return {
                    "chunks": result["text_chunks"],
                    "metadata": {
                        "file_type": file_type,
                        "structured_data": result["structured_data"],
                        "aggregation_metadata": result.get("aggregation_metadata", {})
                    }
                }
            else:
                chunks = await processors[file_type](file_path)
                return {
                    "chunks": chunks,
                    "metadata": {
                        "file_type": file_type,
                        "chunk_count": len(chunks)
                    }
                }
        except Exception as e:
            logger.error(f"Error in process_file: {str(e)}")
            raise

# Create a singleton instance
document_processor = DocumentProcessor()