import google.generativeai as genai
from app.core.config import settings
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = "models/embedding-001"
        self.max_workers = 3  # Limit concurrent requests to avoid rate limits
        self.batch_size = 10  # Process in smaller batches
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds
        
    async def get_embeddings(self, text: str) -> list[float]:
        """
        Get embeddings for a given text using Google's Gemini API
        
        Args:
            text (str): The text to get embeddings for
            
        Returns:
            list[float]: The embedding vector
        """
        for attempt in range(self.retry_attempts):
            try:
                # Truncate text if it's too long (API limitation)
                if len(text) > 25000:
                    logger.warning(f"Text too long ({len(text)} chars), truncating to 25000 chars")
                    text = text[:25000]
                
                # Use the embedding function directly
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document",
                )
                
                return result['embedding']
                
            except Exception as e:
                logger.error(f"Error getting embeddings (attempt {attempt+1}/{self.retry_attempts}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    raise

    def _process_text_batch(self, batch: List[str]) -> List[List[float]]:
        """Process a batch of texts to get embeddings in a thread"""
        result = []
        for text in batch:
            # This is synchronous for ThreadPoolExecutor
            for attempt in range(self.retry_attempts):
                try:
                    # Truncate text if it's too long (API limitation)
                    if len(text) > 25000:
                        text = text[:25000]
                    
                    embedding_result = genai.embed_content(
                        model=self.model,
                        content=text,
                        task_type="retrieval_document",
                    )
                    
                    result.append(embedding_result['embedding'])
                    break
                except Exception as e:
                    logger.error(f"Batch embedding error (attempt {attempt+1}/{self.retry_attempts}): {str(e)}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                    else:
                        # On final attempt, add None to maintain order
                        result.append(None)
        return result

    async def get_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Get embeddings for multiple texts in batch
        
        Args:
            texts (list[str]): List of texts to get embeddings for
            
        Returns:
            list[list[float]]: List of embedding vectors
        """
        if not texts:
            return []
            
        logger.info(f"Processing batch of {len(texts)} texts for embeddings")
        
        # Process in smaller batches using a thread pool
        all_embeddings = []
        
        # Split into smaller batches
        batches = [texts[i:i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
        logger.info(f"Split into {len(batches)} smaller batches of max {self.batch_size} texts each")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map each batch to the thread pool
            batch_results = list(executor.map(self._process_text_batch, batches))
            
        # Flatten results
        for batch_result in batch_results:
            all_embeddings.extend(batch_result)
            
        # Handle any failed embeddings
        for i, embedding in enumerate(all_embeddings):
            if embedding is None:
                logger.warning(f"Failed to get embedding for text at index {i}, using fallback method")
                try:
                    # Try one more time directly
                    all_embeddings[i] = await self.get_embeddings(texts[i])
                except Exception as e:
                    logger.error(f"Final fallback embedding attempt failed: {str(e)}")
                    # Create a zero vector as last resort
                    # We get the dimension from a successful embedding or use default
                    dim = next((len(emb) for emb in all_embeddings if emb is not None), 768)
                    all_embeddings[i] = [0.0] * dim
        
        return all_embeddings

# Create a singleton instance
embedding_service = EmbeddingService()