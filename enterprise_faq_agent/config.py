from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_package_env = Path(__file__).resolve().parent / ".env"
_root_env = Path(__file__).resolve().parent.parent / ".env"

if _package_env.is_file():
    load_dotenv(_package_env)
elif _root_env.is_file():
    load_dotenv(_root_env)
else:
    load_dotenv()


@dataclass
class Settings:
    google_cloud_project: str = field(
        default_factory=lambda: (
            os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("PROJECT_ID")
            or "enterprise-gcp-project"
        )
    )
    google_cloud_location: str = field(
        default_factory=lambda: (
            os.getenv("GOOGLE_CLOUD_LOCATION")
            or os.getenv("LOCATION")
            or "global"
        )
    )

    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"
    )
    gemini_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )

    agent_gateway_url: Optional[str] = field(
        default_factory=lambda: (
            os.getenv("AGENT_GATEWAY_URL")
            or os.getenv("AGENT_GATEWAY_ENDPOINT")
        )
    )

    discovery_engine_project_id: Optional[str] = field(
        default_factory=lambda: (
            os.getenv("DISCOVERY_ENGINE_PROJECT_ID")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("PROJECT_ID")
        )
    )
    discovery_engine_location: str = field(
        default_factory=lambda: os.getenv("DISCOVERY_ENGINE_LOCATION") or "global"
    )
    discovery_engine_collection_id: str = field(
        default_factory=lambda: (
            os.getenv("DISCOVERY_ENGINE_COLLECTION_ID") or "default_collection"
        )
    )
    discovery_engine_id: str = field(
        default_factory=lambda: (
            os.getenv("DISCOVERY_ENGINE_ID")
            or os.getenv("ENGINE_ID")
            or os.getenv("DISCOVERY_ENGINE_DATA_STORE_ID")
            or "default-search-engine"
        )
    )
    discovery_engine_serving_config_id: str = field(
        default_factory=lambda: (
            os.getenv("DISCOVERY_ENGINE_SERVING_CONFIG_ID")
            or "default_search"
        )
    )
    discovery_engine_page_size: int = field(
        default_factory=lambda: int(os.getenv("DISCOVERY_ENGINE_PAGE_SIZE", "8"))
    )
    discovery_engine_max_extractive_answer_count: int = field(
        default_factory=lambda: int(
            os.getenv("DISCOVERY_ENGINE_MAX_EXTRACTIVE_ANSWER_COUNT", "1")
        )
    )
    discovery_engine_max_extractive_segment_count: int = field(
        default_factory=lambda: int(
            os.getenv("DISCOVERY_ENGINE_MAX_EXTRACTIVE_SEGMENT_COUNT", "2")
        )
    )

    @property
    def discovery_engine_data_store_id(self) -> str:
        return self.discovery_engine_id

    model_armor_enabled: bool = field(
        default_factory=lambda: os.getenv("MODEL_ARMOR_ENABLED", "true").lower()
        in ("true", "1", "yes")
    )
    model_armor_location: Optional[str] = field(
        default_factory=lambda: os.getenv("MODEL_ARMOR_LOCATION")
    )
    model_armor_template_name: Optional[str] = field(
        default_factory=lambda: os.getenv("MODEL_ARMOR_TEMPLATE_NAME")
    )
    model_armor_template_id: str = field(
        default_factory=lambda: (
            os.getenv("MODEL_ARMOR_TEMPLATE_ID")
            or "default-corporate-template"
        )
    )
    model_armor_fail_closed: bool = field(
        default_factory=lambda: os.getenv("MODEL_ARMOR_FAIL_CLOSED", "true").lower()
        in ("true", "1")
    )

    hr_support_email: str = field(
        default_factory=lambda: os.getenv("HR_SUPPORT_EMAIL", "hr-support@corp.internal")
    )
    it_helpdesk_email: str = field(
        default_factory=lambda: os.getenv("IT_HELPDESK_EMAIL", "it-helpdesk@corp.internal")
    )

    port: int = field(
        default_factory=lambda: int(os.getenv("PORT", "8080"))
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )


def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
