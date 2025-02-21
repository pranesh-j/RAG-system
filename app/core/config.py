from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    WEAVIATE_URL: str = "http://localhost:8080"  # Default value
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 102  # 20% overlap
    MAX_CHUNKS_PER_DOC: int = 1000
    SIMILARITY_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"

    @property
    def weaviate_host(self) -> str:
        return self.WEAVIATE_URL.replace("http://", "").replace("https://", "").split(":")[0]

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()