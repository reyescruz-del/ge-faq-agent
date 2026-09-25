import os
from enterprise_faq_agent.config import Settings, get_settings


def test_default_settings(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("PROJECT_ID", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("DISCOVERY_ENGINE_PROJECT_ID", raising=False)
    monkeypatch.delenv("DISCOVERY_ENGINE_ID", raising=False)
    monkeypatch.delenv("ENGINE_ID", raising=False)
    monkeypatch.delenv("DISCOVERY_ENGINE_DATA_STORE_ID", raising=False)
    monkeypatch.delenv("DISCOVERY_ENGINE_LOCATION", raising=False)
    monkeypatch.delenv("DISCOVERY_ENGINE_SERVING_CONFIG_ID", raising=False)
    monkeypatch.delenv("MODEL_ARMOR_ENABLED", raising=False)

    settings = get_settings()
    assert settings.google_cloud_project == "enterprise-gcp-project"
    assert settings.google_cloud_location == "global"
    assert settings.gemini_model == "gemini-3.5-flash"
    assert settings.discovery_engine_project_id is None
    assert settings.discovery_engine_location == "global"
    assert settings.discovery_engine_id == "default-search-engine"
    assert settings.discovery_engine_serving_config_id == "default_search"
    assert settings.model_armor_enabled is True
    assert settings.model_armor_fail_closed is True
    assert settings.port == 8080
    assert settings.log_level == "INFO"


def test_custom_settings(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "custom-gcp-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("DISCOVERY_ENGINE_PROJECT_ID", "custom-ds-project")
    monkeypatch.setenv("DISCOVERY_ENGINE_LOCATION", "eu")
    monkeypatch.setenv("DISCOVERY_ENGINE_ID", "custom-engine")
    monkeypatch.setenv("DISCOVERY_ENGINE_SERVING_CONFIG_ID", "custom_search")
    monkeypatch.setenv("MODEL_ARMOR_ENABLED", "false")
    monkeypatch.setenv("MODEL_ARMOR_FAIL_CLOSED", "0")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = get_settings()
    assert settings.google_cloud_project == "custom-gcp-project"
    assert settings.google_cloud_location == "europe-west1"
    assert settings.gemini_model == "gemini-2.5-pro"
    assert settings.discovery_engine_project_id == "custom-ds-project"
    assert settings.discovery_engine_location == "eu"
    assert settings.discovery_engine_id == "custom-engine"
    assert settings.discovery_engine_serving_config_id == "custom_search"
    assert settings.model_armor_enabled is False
    assert settings.model_armor_fail_closed is False
    assert settings.port == 9090
    assert settings.log_level == "DEBUG"
