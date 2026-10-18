from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "ClientBridge"
    DATABASE_URL: str = "postgresql+asyncpg://clientbridge:clientbridge@localhost:5432/clientbridge"
    DB_ECHO: bool = False

    # CRM
    CRM_BASE_URL: str = "http://localhost:8000"
    CRM_ORDERS_PATH: str = "/mock/crm/orders"
    CRM_TIMEOUT_SECONDS: float = 10.0

    # Worker
    WORKER_CONCURRENCY: int = 4
    POLL_INTERVAL_SECONDS: float = 2.0
    HEARTBEAT_INTERVAL_SECONDS: int = 15
    RECOVERY_INTERVAL_SECONDS: int = 60
    HEARTBEAT_TIMEOUT_SECONDS: int = 300  # 5 dakika

    # Retry
    MAX_RETRIES: int = 5
    BACKOFF_BASE_SECONDS: float = 2.0
    BACKOFF_MAX_SECONDS: float = 300.0


settings = Settings()
