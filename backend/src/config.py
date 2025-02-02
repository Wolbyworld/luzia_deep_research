from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Environment
    APP_ENV = os.getenv("APP_ENV", "development")
    
    # API Keys (from .env)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    
    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))  # 24 hours
    
    # Search Settings
    MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "10"))
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "azure")  # azure or serper
    
    # Content Processing
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
    MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", "100"))
    MAX_CHUNKS_FOR_REPORT = int(os.getenv("MAX_CHUNKS_FOR_REPORT", "5"))
    
    # Model Settings
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
    
    # Rate Limiting
    RATE_LIMIT_SEARCH = int(os.getenv("RATE_LIMIT_SEARCH", "5"))  # requests per minute
    RATE_LIMIT_CONTENT = int(os.getenv("RATE_LIMIT_CONTENT", "20"))
    RATE_LIMIT_AI = int(os.getenv("RATE_LIMIT_AI", "5"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all configuration values as a dictionary"""
        return {key: value for key, value in cls.__dict__.items() 
                if not key.startswith('_') and not callable(value)} 