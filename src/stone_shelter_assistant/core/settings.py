"""Application configuration. Define validated settings with pydantic-settings. Read environment configuration without committing secrets."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    selection_json_schema_models: frozenset[str]
    parsing_model: str | None = Field(default=None, min_length=1)
    evaluation_model: str = Field(min_length=1)
    evaluation_max_tokens: int = Field(default=8192, ge=1)
    evaluation_request_timeout: int = Field(default=180_000, gt=0)
    evaluation_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "medium"
    max_tokens: int = Field(default=3072, ge=1)
    max_retries: int = Field(default=0, ge=0)
    request_timeout: int = Field(default=45_000, gt=0)
    evaluation_json_schema_models: frozenset[str]
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
    base_url: str = Field(min_length=1)
