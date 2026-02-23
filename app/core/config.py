"""
MetaPM Configuration
Environment-based settings management
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Version
    VERSION: str = "2.3.11"  # Data sprint: AF-030 Prompt Moderation Pre-Check requirement added
    BUILD: str = os.getenv("COMMIT_SHA", os.getenv("BUILD_ID", "unknown"))
    
    # Database
    DB_SERVER: str = "localhost"
    DB_NAME: str = "MetaPM"
    DB_USER: str = "sqlserver"
    DB_PASSWORD: str = ""
    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"
    
    # GCP
    GCP_PROJECT_ID: str = ""
    CLOUD_SQL_INSTANCE: str = ""
    GCS_MEDIA_BUCKET: str = "metapm-media"
    
    # AI APIs
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Security
    API_KEY: str = ""
    MCP_API_KEY: str = ""  # API key for MCP endpoints

    # GCS Handoff Bridge
    GCS_HANDOFF_BUCKET: str = "corey-handoff-bridge"
    
    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # CORS - allow all origins in dev, restrict in production
    # "null" is needed for file:// origins (local HTML files)
    CORS_ORIGINS: List[str] = ["*", "null"]
    
    @property
    def database_url(self) -> str:
        """Build pyodbc connection string"""
        # For Cloud Run with Cloud SQL proxy
        if self.DB_SERVER.startswith("/cloudsql/"):
            return (
                f"DRIVER={{{self.DB_DRIVER}}};"
                f"SERVER={self.DB_SERVER};"
                f"DATABASE={self.DB_NAME};"
                f"UID={self.DB_USER};"
                f"PWD={self.DB_PASSWORD};"
                "TrustServerCertificate=yes;"
            )
        # For local development or direct IP connection
        return (
            f"DRIVER={{{self.DB_DRIVER}}};"
            f"SERVER={self.DB_SERVER};"
            f"DATABASE={self.DB_NAME};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
            "TrustServerCertificate=yes;"
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
