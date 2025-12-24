"""Configuration settings for the Geospatial AI Co-Scientist."""

from enum import Enum
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="LLM provider to use"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    azure_openai_api_key: Optional[str] = Field(
        default=None,
        description="Azure OpenAI API key"
    )
    azure_openai_endpoint: Optional[str] = Field(
        default=None,
        description="Azure OpenAI endpoint"
    )

    # Model selection
    generation_model: str = Field(
        default="gpt-4-turbo-preview",
        description="Model for hypothesis generation"
    )
    reflection_model: str = Field(
        default="gpt-4-turbo-preview",
        description="Model for reflection/review"
    )
    ranking_model: str = Field(
        default="gpt-4-turbo-preview",
        description="Model for ranking"
    )
    fast_model: str = Field(
        default="gpt-3.5-turbo",
        description="Fast model for simple tasks"
    )

    # Model parameters
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for generation"
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens for generation"
    )

    # Literature search
    semantic_scholar_api_key: Optional[str] = Field(
        default=None,
        description="Semantic Scholar API key"
    )
    search_results_limit: int = Field(
        default=20,
        description="Maximum number of search results to retrieve"
    )

    # Vector store
    vector_store_type: str = Field(
        default="chroma",
        description="Vector store type (chroma, faiss)"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model for vector store"
    )
    chroma_persist_directory: str = Field(
        default="./data/chroma_db",
        description="Directory for ChromaDB persistence"
    )

    # Workflow settings
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum generation-refinement iterations"
    )
    hypotheses_per_iteration: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of hypotheses to generate per iteration"
    )
    top_hypotheses_to_evolve: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of top hypotheses to evolve"
    )
    ranking_comparisons: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of pairwise comparisons for ranking"
    )

    # Elo rating settings
    initial_elo_score: float = Field(
        default=1000.0,
        description="Initial Elo score for new hypotheses"
    )
    elo_k_factor: float = Field(
        default=32.0,
        description="K-factor for Elo rating updates"
    )

    # Checkpoints and human-in-the-loop
    checkpoint_after_generation: bool = Field(
        default=False,
        description="Pause for human review after generation"
    )
    checkpoint_after_ranking: bool = Field(
        default=False,
        description="Pause for human review after ranking"
    )
    checkpoint_before_final: bool = Field(
        default=True,
        description="Pause for human review before final output"
    )

    # Logging and monitoring
    langsmith_api_key: Optional[str] = Field(
        default=None,
        description="LangSmith API key for tracing"
    )
    langsmith_project: str = Field(
        default="geospatial-co-scientist",
        description="LangSmith project name"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )

    # Caching
    enable_caching: bool = Field(
        default=True,
        description="Enable response caching"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache TTL in seconds"
    )

    # Data analysis
    enable_code_execution: bool = Field(
        default=False,
        description="Enable code execution for data analysis"
    )
    sandbox_type: str = Field(
        default="docker",
        description="Sandbox type for code execution"
    )

    # API settings
    api_host: str = Field(
        default="0.0.0.0",
        description="API host"
    )
    api_port: int = Field(
        default=8000,
        description="API port"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "GEO_SCIENTIST_"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def update_settings(**kwargs) -> Settings:
    """Update settings with new values."""
    global settings
    current_dict = settings.model_dump()
    current_dict.update(kwargs)
    settings = Settings(**current_dict)
    return settings
