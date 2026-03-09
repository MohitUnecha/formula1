"""Application configuration management"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    # Pydantic v2: avoid 'model_' protected namespace conflict for 'model_dir'
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=("settings_",),
    )
    
    # Database
    database_url: str = "sqlite:///./f1.db"
    database_pool_size: int = 3
    database_max_overflow: int = 0
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # FastF1
    fastf1_cache_dir: Path = Path("./data/fastf1_cache")
    fastf1_cache_enabled: bool = True
    
    # Data Storage
    data_dir: Path = Path("./data")
    parquet_dir: Path = Path("./data/telemetry")
    model_dir: Path = Path("./models")
    
    # ML Config
    ml_training_enabled: bool = True
    ml_lookback_races: int = 10
    ml_retrain_schedule: str = "0 2 * * 1"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_reload: bool = False
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Monitoring
    prometheus_enabled: bool = True
    log_level: str = "INFO"
    
    # Feature Flags
    enable_live_mode: bool = False
    enable_websocket: bool = True

    # Groq LLM (Primary + Fallback)
    groq_api_key: str | None = None
    groq_model: str = "mixtral-8x7b-32768"
    groq_timeout: float = 12.0  # seconds
    groq_temperature: float = 0.35

    # Tavily Search (predictions only, current season)
    tavily_api_key: str | None = None
    tavily_timeout: float = 15.0

    # Gemini AI (tandem with Groq, rate-limited)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    gemini_timeout: float = 15.0
    gemini_temperature: float = 0.3
    
    # DeepSeek AI (Deep reasoning)
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: float = 15.0
    
    # Multi-AI System Configuration
    # The multi_ai_client.py uses hardcoded keys for reliability
    # but these can be overridden via environment variables
    # See services/multi_ai_client.py for the full AI provider setup:
    # - 2x Gemini Pro (Strategy + Data Analysis)
    # - 1x DeepSeek (Deep Reasoning)  
    # - 2x Groq Mixtral (Quick Analysis + Fallback)


# Global settings instance
settings = Settings()

# Create directories if they don't exist
settings.fastf1_cache_dir.mkdir(parents=True, exist_ok=True)
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.parquet_dir.mkdir(parents=True, exist_ok=True)
settings.model_dir.mkdir(parents=True, exist_ok=True)
