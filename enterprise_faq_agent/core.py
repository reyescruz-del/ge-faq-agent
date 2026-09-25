from __future__ import annotations

import logging
from typing import Any, Optional

from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import modelarmor_v1
from google.genai import types

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App

from .config import Settings, get_settings
from .prompts import SYSTEM_INSTRUCTION
from .tools import search_corporate_faq

logger = logging.getLogger(__name__)


class SecurityGovernanceError(Exception):
    def __init__(
        self,
        message: str,
        violation_type: str,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.violation_type = violation_type
        self.details = details or {}


_model_armor_client: Optional[modelarmor_v1.ModelArmorAsyncClient] = None
_model_armor_endpoint: Optional[str] = None


def _get_model_armor_client(location: str) -> Optional[modelarmor_v1.ModelArmorAsyncClient]:
    global _model_armor_client, _model_armor_endpoint
    api_endpoint = f"modelarmor.{location}.rep.googleapis.com"
    if _model_armor_client is not None and _model_armor_endpoint == api_endpoint:
        return _model_armor_client

    try:
        client_options = ClientOptions(api_endpoint=api_endpoint)
        _model_armor_client = modelarmor_v1.ModelArmorAsyncClient(client_options=client_options)
        _model_armor_endpoint = api_endpoint
        logger.info("ModelArmorAsyncClient initialized targeting endpoint: %s", api_endpoint)
        return _model_armor_client
    except Exception as exc:
        logger.warning("Failed to initialize ModelArmorAsyncClient: %s", exc)
        return None


async def sanitize_prompt_with_armor(
    prompt: str,
    *,
    settings: Optional[Settings] = None,
    client: Optional[modelarmor_v1.ModelArmorAsyncClient] = None,
) -> tuple[str, bool, dict[str, Any]]:
    cfg = settings or get_settings()
    if not cfg.model_armor_enabled:
        return prompt, False, {"model_armor_screened": False}

    loc = cfg.model_armor_location or cfg.google_cloud_location or "us-central1"
    armor_client = client or _get_model_armor_client(loc)
    template_name = cfg.model_armor_template_name
    if not template_name and cfg.google_cloud_project:
        template_name = (
            f"projects/{cfg.google_cloud_project}/locations/{loc}"
            f"/templates/{cfg.model_armor_template_id}"
        )

    if not armor_client or not template_name:
        logger.debug("Model Armor skipped: client or template unconfigured.")
        return prompt, False, {"model_armor_screened": False}

    request = modelarmor_v1.SanitizeUserPromptRequest(
        name=template_name,
        user_prompt_data=modelarmor_v1.DataItem(text=prompt),
    )

    try:
        response: modelarmor_v1.SanitizeUserPromptResponse = (
            await armor_client.sanitize_user_prompt(request=request)
        )
    except GoogleAPICallError as api_err:
        logger.error("Model Armor API call failed: %s", api_err.message, exc_info=True)
        if cfg.model_armor_fail_closed:
            raise SecurityGovernanceError(
                message="Security screening service unavailable. Request blocked under fail-closed policy.",
                violation_type="MODEL_ARMOR_SERVICE_ERROR",
                details={"error": api_err.message},
            ) from api_err
        return prompt, False, {"model_armor_screened": False, "error": api_err.message}
    except Exception as exc:
        logger.error("Unexpected error in Model Armor screening: %s", exc, exc_info=True)
        if cfg.model_armor_fail_closed:
            raise SecurityGovernanceError(
                message="Internal security screening error occurred.",
                violation_type="MODEL_ARMOR_INTERNAL_ERROR",
                details={"error": str(exc)},
            ) from exc
        return prompt, False, {"model_armor_screened": False, "error": str(exc)}

    result = response.sanitization_result
    details: dict[str, Any] = {
        "model_armor_screened": True,
        "filter_match_state": str(result.filter_match_state),
        "invocation_result": str(result.invocation_result),
    }

    pi_filter = result.filter_results.get("pi_and_jailbreak")
    if pi_filter and pi_filter.match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
        logger.warning("Prompt Injection or Jailbreak detected by Model Armor.")
        raise SecurityGovernanceError(
            message="Security Policy Violation: Your request was blocked due to detected Prompt Injection or Jailbreak risk.",
            violation_type="PROMPT_INJECTION_DETECTED",
            details=details,
        )

    active_prompt = prompt
    was_modified = False
    sdp_filter = result.filter_results.get("sdp")
    if sdp_filter:
        deidentify = sdp_filter.deidentify_result
        if deidentify and deidentify.data and deidentify.data.text:
            logger.info("Model Armor de-identified PII in user prompt.")
            active_prompt = deidentify.data.text
            was_modified = True
            details["pii_deidentified"] = True
            details["transformed_bytes"] = deidentify.transformed_bytes
        elif sdp_filter.match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
            logger.warning("Model Armor flagged unauthorized PII leakage.")
            raise SecurityGovernanceError(
                message="Security Policy Violation: Your request contains unauthorized Sensitive / Personally Identifiable Information (PII).",
                violation_type="PII_LEAKAGE_DETECTED",
                details=details,
            )

    if (
        result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND
        and not was_modified
    ):
        logger.warning("Model Armor general filter violation matched.")
        raise SecurityGovernanceError(
            message="Security Policy Violation: Prompt violated corporate safety and compliance filters.",
            violation_type="GENERAL_SAFETY_VIOLATION",
            details=details,
        )

    return active_prompt, was_modified, details


async def model_armor_guardrail_callback(ctx: CallbackContext) -> Optional[types.Content]:
    settings = get_settings()
    if not settings.model_armor_enabled:
        return None

    if not ctx.user_content or not ctx.user_content.parts:
        return None

    user_text_parts = [p.text for p in ctx.user_content.parts if p.text]
    if not user_text_parts:
        return None

    raw_prompt = " ".join(user_text_parts)
    try:
        sanitized_prompt, was_modified, _ = await sanitize_prompt_with_armor(
            raw_prompt, settings=settings
        )
        if was_modified:
            ctx.user_content.parts = [types.Part.from_text(text=sanitized_prompt)]
        return None
    except SecurityGovernanceError as sec_err:
        logger.warning("Model Armor blocked prompt in ADK callback: %s", sec_err.message)
        return types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=f"Security Policy Violation: {sec_err.message}"
                )
            ],
        )


def create_agent(settings: Optional[Settings] = None) -> Agent:
    cfg = settings or get_settings()

    return Agent(
        name="enterprise_faq_agent",
        description="Corporate HR & IT Assistant powered by Vertex AI Search Enterprise and Gemini",
        instruction=SYSTEM_INSTRUCTION,
        model=cfg.gemini_model,
        tools=[search_corporate_faq],
        before_agent_callback=model_armor_guardrail_callback,
    )


agent: Agent = create_agent()
root_agent: Agent = agent
app: App = App(
    name="enterprise_faq_agent",
    root_agent=root_agent,
)

__all__ = [
    "agent",
    "root_agent",
    "app",
    "create_agent",
    "SecurityGovernanceError",
    "model_armor_guardrail_callback",
    "sanitize_prompt_with_armor",
]
