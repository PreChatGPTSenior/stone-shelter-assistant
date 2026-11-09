"""Tests for database configuration validation."""

import pytest
from pydantic import SecretStr, ValidationError

from stone_shelter_assistant.core.settings import DatabaseSettings


def test_database_settings_reject_invalid_port() -> None:
    with pytest.raises(ValidationError) as error:
        DatabaseSettings(
            _env_file=None,
            host="localhost",
            port=70000,
            db="test_database",
            user="test_user",
            password=SecretStr("test_password"),
        )

    assert any(
        item["loc"] == ("port",) and item["type"] == "less_than_equal"
        for item in error.value.errors()
    )


def test_database_settings_accept_valid() -> None:
    settings = DatabaseSettings(
        _env_file=None,
        host="localhost",
        port=5432,
        db="test_database",
        user="test_user",
        password=SecretStr("test_password"),
    )
    assert settings.host == "localhost"
    assert settings.port == 5432
    assert settings.db == "test_database"
    assert settings.user == "test_user"
    assert settings.password.get_secret_value() == "test_password"


def test_database_settings_reject_not_exist_require_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    with pytest.raises(ValidationError) as error:
        DatabaseSettings(
            _env_file=None,
            host="localhost",
            port=5324,
            user="test_user",
            password=SecretStr("test_password"),
        )
    assert any(
        item["loc"] == ("db",) and item["type"] == "missing" for item in error.value.errors()
    )


def test_database_settings_env_load_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5324")
    monkeypatch.setenv("POSTGRES_USER", "test_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")
    monkeypatch.setenv("POSTGRES_DB", "test_database")

    settings = DatabaseSettings(
        _env_file=None,
    )
    assert settings.host == "localhost"
    assert settings.port == 5324
    assert settings.db == "test_database"
    assert settings.user == "test_user"
    assert settings.password.get_secret_value() == "test_password"
