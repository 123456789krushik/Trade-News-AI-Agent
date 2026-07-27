from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application configuration validated using Pydantic Settings.
    Reads from environment variables and falls back to a local .env file.
    """
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///tradeflow.db", 
        description="Async SQLite Database URL using aiosqlite driver"
    )

    # API Keys
    GEMINI_API_KEY: str = Field(default="mock_gemini_key", description="Google Gemini API Access Key")
    NEWS_API_KEY: str = Field(default="mock_newsapi_key", description="NewsAPI.org Access Key")

    # Load configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
