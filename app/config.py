import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Groq configurations
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # Qdrant configurations
    QDRANT_PATH: Optional[str] = "./qdrant_data"
    QDRANT_URL: Optional[str] = None
    
    # General App configurations
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Collection name for support docs in Qdrant
    QDRANT_COLLECTION_NAME: str = "support_knowledge_base"

    # Admin panel password (change in .env for production)
    ADMIN_PASSWORD: str = "admin123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
