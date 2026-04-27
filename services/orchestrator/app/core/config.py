from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    postgres_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/research"
    openai_api_key: str = ""
    tavily_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""


settings = Settings()
