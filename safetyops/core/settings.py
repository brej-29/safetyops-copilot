from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "SafetyOps Copilot"
    app_version: str = "0.1.0"
    env: str = "local"
    log_level: str = "INFO"

    # Deployment
    deploy_mode: str = "local"  # local | cloud

    # Streaming / Redis
    redis_url: str = "redis://localhost:6379"
    stream_key: str = "safetyops:events"
    consumer_group: str = "safetyops-workers"
    consumer_name: str = "worker-1"
    dlq_stream_key: str = "safetyops:events:dlq"

    # Database
    database_url: str = "postgresql+psycopg2://safetyops:safetyops@localhost:5432/safetyops"

    # MLflow tracking
    mlflow_tracking_uri: str | None = "http://localhost:5000"

    # Model and artifacts locations
    artifacts_dir: str = "artifacts"
    nlp_model_dir: str = "models/nlp"
    vision_model_path: str = "yolov8n.pt"

    # Optional LLM for Copilot report enhancement. Any OpenAI-compatible
    # chat-completions endpoint works, e.g.:
    #   Groq:   llm_base_url=https://api.groq.com/openai  (needs llm_api_key)
    #   Ollama: llm_base_url=http://localhost:11434       (no key needed)
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    # Deprecated aliases (kept for backwards compatibility; used when the
    # llm_* settings above are unset).
    ollama_base_url: str | None = None
    ollama_model: str | None = None

    # Metrics
    metrics_namespace: str = "safetyops"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SAFETYOPS_",
        extra="ignore",
    )


settings = Settings()