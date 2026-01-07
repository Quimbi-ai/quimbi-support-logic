"""
Configuration management for AI-First CRM.

Uses Pydantic Settings for type-safe configuration.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    environment: str = "development"

    # API
    api_key: str
    api_base_url: str = "http://localhost:8000"

    # Security (JWT)
    secret_key: str  # REQUIRED - Use: openssl rand -hex 32
    access_token_expire_hours: int = 24  # JWT token validity

    # Database
    database_url: str

    # AI Services (Legacy - replaced by Quimbi)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Quimbi Backend Integration
    quimbi_base_url: str = "https://ecommerce-backend-staging-a14c.up.railway.app"
    quimbi_api_key: str  # REQUIRED - Get from Quimbi admin
    quimbi_timeout: float = 30.0
    quimbi_max_retries: int = 3

    # Quimbi Caching Configuration
    quimbi_cache_intelligence_ttl: int = 900  # 15 minutes (customer DNA, archetype)
    quimbi_cache_churn_ttl: int = 3600  # 1 hour (churn predictions)
    quimbi_cache_ltv_ttl: int = 3600  # 1 hour (LTV forecasts)

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Scoring Service Configuration
    scoring_recalculation_interval: int = 300  # 5 minutes
    scoring_churn_weight: float = 3.0
    scoring_value_weight: float = 2.0
    scoring_urgency_weight: float = 1.5
    topic_alert_boost: float = 5.0

    # Draft Generation
    draft_cache_ttl: int = 3600  # 1 hour
    draft_llm_provider: str = "anthropic"  # openai or anthropic
    draft_model: str = "claude-3-5-sonnet-20241022"

    # Context Gathering
    context_max_past_tickets: int = 5
    context_max_recent_orders: int = 3

    # Gorgias Integration
    gorgias_domain: str  # REQUIRED - e.g., "lindas"
    gorgias_api_key: str  # REQUIRED - Gorgias API key
    gorgias_username: str  # REQUIRED - e.g., "lindas.quimbiai@proton.me"
    gorgias_webhook_secret: str | None = None  # Optional - for signature validation

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
