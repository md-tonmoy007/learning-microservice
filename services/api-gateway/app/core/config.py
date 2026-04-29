from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    orchestrator_url: str = "http://orchestrator:8001"
    kafka_bootstrap_servers: str = "redpanda:9092"
    redis_url: str = "redis://redis:6379"


settings = Settings()
