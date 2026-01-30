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
    VERSION: str = "1.4.3"  # DIAGNOSTIC: Testing if code actually deploys
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
    
    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # CORS - allow all origins in dev, restrict in production
    CORS_ORIGINS: List[str] = ["*"]
    
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
