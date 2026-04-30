from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    postgres_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/research"
    tavily_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    planner_agent_address: str = "planner-agent:50051"
    search_agent_address: str = "search-agent:50052"
    summarizer_agent_address: str = "summarizer-agent:50053"
    critic_agent_address: str = "critic-agent:50054"
    report_service_address: str = "report-service:50055"
    kafka_bootstrap_servers: str = "redpanda:9092"
    redis_url: str = "redis://redis:6379"
    otel_endpoint: str = "http://otel-collector:4317"


settings = Settings()
