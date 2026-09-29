from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_package_env: Path = Path(__file__).resolve().parent / ".env"
_root_env: Path = Path(__file__).resolve().parent.parent / ".env"

if _package_env.is_file():
    load_dotenv(_package_env)
elif _root_env.is_file():
    load_dotenv(_root_env)
else:
    load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    google_cloud_project: str = Field(
        default="enterprise-gcp-project",
        validation_alias=AliasChoices(
            "GOOGLE_CLOUD_PROJECT", "PROJECT_ID", "google_cloud_project"
        ),
        description="Google Cloud Project ID.",
    )
    google_cloud_location: str = Field(
        default="global",
        validation_alias=AliasChoices(
            "GOOGLE_CLOUD_LOCATION", "LOCATION", "google_cloud_location"
        ),
        description="Vertex AI model location.",
    )

    gemini_model: str = Field(
        default="gemini-3.5-flash",
        validation_alias=AliasChoices("GEMINI_MODEL", "gemini_model"),
        description="Foundation Gemini model name.",
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "GEMINI_API_KEY", "GOOGLE_API_KEY", "gemini_api_key"
        ),
        description="Optional Gemini API key.",
    )

    agent_gateway_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "AGENT_GATEWAY_URL", "AGENT_GATEWAY_ENDPOINT", "agent_gateway_url"
        ),
        description="Optional Agent Gateway URL endpoint.",
    )

    discovery_engine_project_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "DISCOVERY_ENGINE_PROJECT_ID",
            "GOOGLE_CLOUD_PROJECT",
            "PROJECT_ID",
            "discovery_engine_project_id",
        ),
        description="Discovery Engine GCP Project ID.",
    )
    discovery_engine_location: str = Field(
        default="global",
        validation_alias=AliasChoices(
            "DISCOVERY_ENGINE_LOCATION", "discovery_engine_location"
        ),
        description="Discovery Engine Search location.",
    )
    discovery_engine_collection_id: str = Field(
        default="default_collection",
        validation_alias=AliasChoices(
            "DISCOVERY_ENGINE_COLLECTION_ID", "discovery_engine_collection_id"
        ),
        description="Discovery Engine collection ID.",
    )
    discovery_engine_id: str = Field(
        default="default-search-engine",
        validation_alias=AliasChoices(
            "DISCOVERY_ENGINE_ID",
            "ENGINE_ID",
            "DISCOVERY_ENGINE_DATA_STORE_ID",
            "discovery_engine_id",
        ),
        description="Discovery Engine Search Engine ID.",
    )
    discovery_engine_serving_config_id: str = Field(
        default="default_search",
        validation_alias=AliasChoices(
            "DISCOVERY_ENGINE_SERVING_CONFIG_ID",
            "discovery_engine_serving_config_id",
        ),
        description="Discovery Engine serving configuration ID.",
    )
    discovery_engine_page_size: int = Field(
        default=8,
        validation_alias=AliasChoices(
            "DISCOVERY_ENGINE_PAGE_SIZE", "discovery_engine_page_size"
        ),
        description="Maximum search results to retrieve per query.",
    )
    discovery_engine_max_extractive_answer_count: int = Field(
        default=1,
        validation_alias=AliasChoices(
            "DISCOVERY_ENGINE_MAX_EXTRACTIVE_ANSWER_COUNT",
            "discovery_engine_max_extractive_answer_count",
        ),
        description="Max extractive answers returned per document.",
    )
    discovery_engine_max_extractive_segment_count: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "DISCOVERY_ENGINE_MAX_EXTRACTIVE_SEGMENT_COUNT",
            "discovery_engine_max_extractive_segment_count",
        ),
        description="Max extractive paragraph segments returned per document.",
    )

    @property
    def discovery_engine_data_store_id(self) -> str:
        """Return the search engine ID as an alias property for backwards compatibility."""
        return self.discovery_engine_id

    model_armor_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("MODEL_ARMOR_ENABLED", "model_armor_enabled"),
        description="Enable or disable Model Armor prompt screening.",
    )
    model_armor_location: Optional[str] = Field(
        default="us-central1",
        validation_alias=AliasChoices("MODEL_ARMOR_LOCATION", "model_armor_location"),
        description="Regional location for Model Armor endpoint.",
    )
    model_armor_template_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "MODEL_ARMOR_TEMPLATE_NAME", "model_armor_template_name"
        ),
        description="Full resource path of the Model Armor security template.",
    )
    model_armor_template_id: str = Field(
        default="faq-security-template",
        validation_alias=AliasChoices(
            "MODEL_ARMOR_TEMPLATE_ID", "model_armor_template_id"
        ),
        description="Template ID of the Model Armor security template.",
    )
    model_armor_fail_closed: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "MODEL_ARMOR_FAIL_CLOSED", "model_armor_fail_closed"
        ),
        description="Whether to block requests if Model Armor screening fails.",
    )

    hr_support_email: str = Field(
        default="hr-support@corp.internal",
        validation_alias=AliasChoices("HR_SUPPORT_EMAIL", "hr_support_email"),
        description="Corporate HR Support email address for unverified HR queries.",
    )
    it_helpdesk_email: str = Field(
        default="it-helpdesk@corp.internal",
        validation_alias=AliasChoices("IT_HELPDESK_EMAIL", "it_helpdesk_email"),
        description="Enterprise IT Help Desk email address for unverified IT queries.",
    )

    port: int = Field(
        default=8080,
        validation_alias=AliasChoices("PORT", "port"),
        description="Server port.",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL", "log_level"),
        description="Logging verbosity level.",
    )

    @field_validator("log_level", mode="after")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        """Normalize log level string to uppercase."""
        return v.upper()


def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
