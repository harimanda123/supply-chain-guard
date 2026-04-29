from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from langchain_core.language_models.chat_models import BaseChatModel


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = Field(default="development")
    app_name: str = Field(default="supply-chain-guard")
    secret_key: str = Field(default="dev-secret-key")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/supply_chain_guard.db"
    )

    # LLM Provider
    llm_provider: str = Field(default="groq")
    llm_model: str = Field(default="llama-3.3-70b-versatile")

    # Provider API keys — all optional, only the active one is needed
    anthropic_api_key: str = Field(default="")
    groq_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    ollama_base_url: str = Field(default="http://localhost:11434")

    # LangSmith tracing — optional, leave blank to disable
    langsmith_api_key: str = Field(default="")
    langsmith_project: str = Field(default="supply-chain-guard")
    langsmith_tracing: bool = Field(default=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_llm() -> BaseChatModel:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
        )

    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.llm_model,
            api_key=settings.groq_api_key,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Choose from: anthropic, groq, openai, ollama"
        )