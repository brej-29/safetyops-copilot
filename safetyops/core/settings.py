from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "SafetyOps Copilot"
    app_version: str = "0.1.0"
    env: str = "local"
    log_level: str = "INFO"

    # Streaming / Redis
    redis_url: str = "redis://localhost:6379"
    stream_key: str = "safetyops:events"
    consumer_group: str = "safetyops-workers"
    consumer_name: str = "worker-1"

    # Database
    database_url: str = "postgresql+psycopg2://safetyops:safetyops@localhost:5432/safetyops"

    # MLflow tracking
    mlflow_tracking_uri: str | None = "http://localhost:5000"

    # Metrics
    metrics_namespace: str = "safetyops"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SAFETYOPS_",
        extra="ignore",
    )


settings = Settings()