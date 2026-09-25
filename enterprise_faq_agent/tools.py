from __future__ import annotations

import collections.abc
import logging
import re
from typing import Any, Optional

from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import discoveryengine_v1 as discoveryengine

from .config import get_settings

logger = logging.getLogger(__name__)

_search_client: Optional[discoveryengine.SearchServiceClient] = None
_client_location: Optional[str] = None


def _clean_html_tags(raw_text: str) -> str:
    if not raw_text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", str(raw_text))
    return " ".join(cleaned.split())


def _safe_get(data: Any, key: str, default: Any = None) -> Any:
    if data is None:
        return default
    if isinstance(data, collections.abc.Mapping):
        return data.get(key, default)
    if hasattr(data, key):
        try:
            val = getattr(data, key)
            if not callable(val) and val is not None and val != "":
                return val
        except Exception:
            pass
    if hasattr(data, "get") and callable(data.get):
        try:
            val = data.get(key)
            if val is not None and not str(type(val)).endswith("MagicMock'>"):
                return val
        except Exception:
            pass
    return default


def _get_search_client(location: str) -> discoveryengine.SearchServiceClient:
    global _search_client, _client_location
    if _search_client is not None and _client_location == location:
        return _search_client

    client_options: Optional[ClientOptions] = None
    if location and location.lower() != "global":
        api_endpoint = f"{location}-discoveryengine.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)
        logger.info("Initializing regional Discovery Engine client targeting endpoint: %s", api_endpoint)
    else:
        logger.info("Initializing global Discovery Engine client.")

    _search_client = discoveryengine.SearchServiceClient(client_options=client_options)
    _client_location = location
    return _search_client


def search_corporate_faq(query: str) -> str:
    settings = get_settings()
    project_id = settings.discovery_engine_project_id
    if not project_id:
        err_msg = (
            "Configuration error: GCP Project ID is not set. Please configure "
            "DISCOVERY_ENGINE_PROJECT_ID or GOOGLE_CLOUD_PROJECT."
        )
        logger.error(err_msg)
        return err_msg

    location = settings.discovery_engine_location
    collection_id = settings.discovery_engine_collection_id
    engine_id = settings.discovery_engine_id
    serving_config_id = settings.discovery_engine_serving_config_id
    page_size = settings.discovery_engine_page_size

    try:
        client = _get_search_client(location)

        serving_config_path = (
            f"projects/{project_id}/locations/{location}/collections/{collection_id}"
            f"/engines/{engine_id}/servingConfigs/{serving_config_id}"
        )

        logger.info(
            "Executing Enterprise Vertex AI Search query: '%s' against resource: %s",
            query,
            serving_config_path,
        )

        content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
            ),
            extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_answer_count=settings.discovery_engine_max_extractive_answer_count,
                max_extractive_segment_count=settings.discovery_engine_max_extractive_segment_count,
                return_extractive_segment_score=True,
            ),
        )

        request = discoveryengine.SearchRequest(
            serving_config=serving_config_path,
            query=query.strip(),
            page_size=page_size,
            content_search_spec=content_search_spec,
        )

        response = client.search(request=request)

        snippets: list[str] = []
        for index, result in enumerate(response.results, start=1):
            doc = getattr(result, "document", None)
            chunk = getattr(result, "chunk", None)
            doc_title = "Corporate FAQ Document"
            doc_uri = ""
            extracted_texts: list[str] = []

            derived = _safe_get(doc, "derived_struct_data")
            if derived:
                doc_title = _safe_get(derived, "title") or _safe_get(derived, "name") or doc_title
                doc_uri = _safe_get(derived, "link") or _safe_get(derived, "uri") or doc_uri

                segments = _safe_get(derived, "extractive_segments", [])
                if isinstance(segments, (list, collections.abc.Sequence)):
                    for seg in segments:
                        raw_seg = _safe_get(seg, "content") or _safe_get(seg, "segment") or _safe_get(seg, "text")
                        if raw_seg:
                            cleaned = _clean_html_tags(str(raw_seg))
                            if cleaned:
                                extracted_texts.append(cleaned)

                if not extracted_texts:
                    answers = _safe_get(derived, "extractive_answers", [])
                    if isinstance(answers, (list, collections.abc.Sequence)):
                        for ans in answers:
                            raw_ans = _safe_get(ans, "content") or _safe_get(ans, "answer") or _safe_get(ans, "text")
                            if raw_ans:
                                cleaned = _clean_html_tags(str(raw_ans))
                                if cleaned:
                                    extracted_texts.append(cleaned)

                if not extracted_texts:
                    snippets_list = _safe_get(derived, "snippets", [])
                    if isinstance(snippets_list, (list, collections.abc.Sequence)):
                        for item in snippets_list:
                            raw_snip = _safe_get(item, "snippet") or _safe_get(item, "text")
                            if raw_snip:
                                cleaned = _clean_html_tags(str(raw_snip))
                                if cleaned:
                                    extracted_texts.append(cleaned)

            if chunk and not extracted_texts:
                chunk_content = getattr(chunk, "content", None)
                if chunk_content:
                    cleaned_chunk = _clean_html_tags(str(chunk_content))
                    if cleaned_chunk:
                        extracted_texts.append(cleaned_chunk)

                chunk_meta = getattr(chunk, "document_metadata", None)
                if chunk_meta:
                    if doc_title == "Corporate FAQ Document":
                        doc_title = _safe_get(chunk_meta, "title") or doc_title
                    if not doc_uri:
                        doc_uri = _safe_get(chunk_meta, "uri") or ""

            struct = _safe_get(doc, "struct_data")
            if struct:
                if doc_title == "Corporate FAQ Document":
                    doc_title = _safe_get(struct, "title") or _safe_get(struct, "name") or doc_title
                if not doc_uri:
                    doc_uri = _safe_get(struct, "link") or _safe_get(struct, "uri") or doc_uri

            if extracted_texts:
                unique_texts: list[str] = []
                seen: set[str] = set()
                for text in extracted_texts:
                    if text not in seen:
                        seen.add(text)
                        unique_texts.append(text)

                combined_excerpt = "\n\n".join(unique_texts)
                header = f"[Source {index}: {doc_title}]"
                if doc_uri:
                    header += f" (URI: {doc_uri})"
                snippets.append(f"{header}\n{combined_excerpt}")

        if not snippets:
            logger.info("No matching snippets retrieved for query: '%s'", query)
            return f"No relevant corporate FAQ documentation found for query: '{query}'."

        result_summary = "\n\n---\n\n".join(snippets)
        logger.info(
            "Successfully retrieved %d relevant snippet section(s) for query: '%s'",
            len(snippets),
            query,
        )
        return result_summary

    except GoogleAPICallError as api_err:
        err_msg = getattr(api_err, "message", str(api_err)) or str(api_err)
        logger.error("Google API error querying Vertex AI Search engine: %s", err_msg, exc_info=True)
        return (
            f"Error querying corporate FAQ knowledge base (Vertex AI Search): {err_msg}. "
            "Please check network connectivity or contact IT infrastructure."
        )
    except Exception as exc:
        logger.error("Unexpected error in search_corporate_faq: %s", str(exc), exc_info=True)
        return (
            f"An unexpected error occurred while searching corporate documents: {str(exc)}. "
            "Please try again or contact IT Help Desk."
        )


__all__ = ["search_corporate_faq", "_clean_html_tags", "_get_search_client"]
