from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "z-ai/glm-4.5-air:free"
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    grpc_port: int = 50054
    otel_endpoint: str = "http://otel-collector:4317"


settings = Settings()
