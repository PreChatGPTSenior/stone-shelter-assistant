"""Application configuration. Define validated settings with pydantic-settings. Read environment configuration without committing secrets."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JSON_SCHEMA_MODELS = frozenset(
    {
        "dots-studio/dots-3-note-preview:free",
        "liquid/lfm-2.5-2.6b:free",
        "liquid/lfm-3-1.7b:free",
        "nvidia/nemotron-3.5-super-vl:free",
        "xingchen-agi/xing4.0-29b-a4b:free",
        "openai/gpt-6-luna",
        "deepseek/deepseek-v4.1-flash",
        "anthropic/claude-sonnet-5",
        "google/gemini-3.8-flash",
        "openai/gpt-6.1-terra",
    }
)


class GroundingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GROUNDING_", env_file=".env", extra="ignore")
    language: str = Field(default="en", pattern=r"^[A-Za-z0-9-]+$")
    catalog_version: str = Field(default="en-v1", pattern=r"^[A-Za-z0-9._-]+$")


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    db: str = Field(min_length=1)
    user: str = Field(min_length=1)
    password: SecretStr = Field(min_length=1)


class TypesenseSettings(BaseSettings):
    """Connection settings for the Typesense search service."""

    model_config = SettingsConfigDict(
        env_prefix="TYPESENSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    protocol: Literal["http", "https"] = "http"
    api_key: SecretStr = Field(min_length=1)
    connection_timeout_seconds: float = Field(default=10.0, gt=0)


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)


class OllamaEmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    base_url: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    embedding_dimension: int = Field(gt=0)


class OpenRouterSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENROUTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
        hide_input_in_errors=True,
    )

    model: str = Field(default="openrouter/free", min_length=1)
    selection_model: str | None = Field(default=None, min_length=1)
    selection_json_schema_models: frozenset[str] = DEFAULT_JSON_SCHEMA_MODELS
    parsing_model: str | None = Field(default=None, min_length=1)
    planning_model: str | None = Field(default=None, min_length=1)
    evaluation_model: str = Field(default="dots-studio/dots-3-note-preview:free", min_length=1)
    evaluation_max_tokens: int = Field(default=8192, ge=1)
    evaluation_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "medium"
    evaluation_json_schema_models: frozenset[str] = DEFAULT_JSON_SCHEMA_MODELS
    answer_model: str | None = Field(default=None, min_length=1)
    api_key: SecretStr = Field(min_length=1)


class LangfuseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LANGFUSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    public_key: str = Field(min_length=1)
    secret_key: SecretStr = Field(min_length=1)
    base_url: str = "https://cloud.langfuse.com"
