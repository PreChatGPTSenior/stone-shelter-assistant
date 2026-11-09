"""Application configuration. Define validated settings with pydantic-settings. Read environment configuration without committing secrets."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
