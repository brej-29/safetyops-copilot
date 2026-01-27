from __future__ import annotations

from safetyops.core.settings import settings


def test_settings_load() -> None:
    assert settings.app_name
    assert settings.database_url
    assert settings.redis_url


def test_api_imports_without_side_effects() -> None:
    # Importing the API app should not require a running database or Redis.
    from apps.api.main import app  # noqa: WPS433

    assert app.title == settings.app_name