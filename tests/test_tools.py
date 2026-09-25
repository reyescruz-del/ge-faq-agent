from unittest.mock import MagicMock, patch

from enterprise_faq_agent.tools import _clean_html_tags, search_corporate_faq


def test_clean_html_tags():
    raw = "<b>Annual Leave</b>:   Employees receive <b>20 days</b> of PTO.  "
    expected = "Annual Leave: Employees receive 20 days of PTO."
    assert _clean_html_tags(raw) == expected


def test_clean_html_tags_empty():
    assert _clean_html_tags("") == ""
    assert _clean_html_tags(None) == ""


def test_search_corporate_faq_missing_project(monkeypatch):
    monkeypatch.delenv("DISCOVERY_ENGINE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("PROJECT_ID", raising=False)

    result = search_corporate_faq("What is the PTO policy?")
    assert "Configuration error: GCP Project ID is not set" in result


def test_search_corporate_faq_success(monkeypatch):
    monkeypatch.setenv("DISCOVERY_ENGINE_PROJECT_ID", "test-project")
    monkeypatch.setenv("DISCOVERY_ENGINE_LOCATION", "global")
    monkeypatch.setenv("DISCOVERY_ENGINE_ID", "corp-faq-engine")
    monkeypatch.setenv("DISCOVERY_ENGINE_SERVING_CONFIG_ID", "default_search")

    mock_client = MagicMock()

    mock_result = MagicMock()
    mock_result.chunk = None
    mock_result.document.name = "doc1"
    mock_result.document.derived_struct_data = {
        "title": "Corporate Leave Policy 2026",
        "link": "gs://corp-bucket/leave_policy.pdf",
        "extractive_segments": [
            {"content": "Full-time employees receive <b>25 days</b> of paid time off annually. Leave must be requested via Workday at least 2 weeks in advance."}
        ],
        "snippets": [
            {"snippet": "Full-time employees receive <b>25 days</b>..."},
        ],
    }
    mock_result.document.struct_data = None

    mock_response = MagicMock()
    mock_response.results = [mock_result]
    mock_client.search.return_value = mock_response

    with patch("enterprise_faq_agent.tools._get_search_client", return_value=mock_client):
        output = search_corporate_faq("How many PTO days do I get?")

        called_request = mock_client.search.call_args.kwargs["request"]
        assert called_request.page_size == 8
        assert called_request.serving_config == (
            "projects/test-project/locations/global/collections/default_collection"
            "/engines/corp-faq-engine/servingConfigs/default_search"
        )
        assert called_request.content_search_spec.snippet_spec.return_snippet is True
        assert called_request.content_search_spec.extractive_content_spec.max_extractive_answer_count == 1
        assert called_request.content_search_spec.extractive_content_spec.max_extractive_segment_count == 2
        assert called_request.content_search_spec.extractive_content_spec.return_extractive_segment_score is True

        assert "Source 1: Corporate Leave Policy 2026" in output
        assert "25 days of paid time off annually." in output
        assert "Leave must be requested via Workday at least 2 weeks in advance." in output
        assert "gs://corp-bucket/leave_policy.pdf" in output


def test_search_corporate_faq_chunk_content(monkeypatch):
    monkeypatch.setenv("DISCOVERY_ENGINE_PROJECT_ID", "test-project")
    monkeypatch.setenv("DISCOVERY_ENGINE_LOCATION", "global")
    monkeypatch.setenv("DISCOVERY_ENGINE_ID", "corp-faq-engine")

    mock_client = MagicMock()

    mock_result = MagicMock()
    mock_result.document = MagicMock()
    mock_result.document.derived_struct_data = {
        "title": "IT Hardware Policy",
        "link": "https://corp.internal/it/hardware",
        "snippets": [],
    }
    mock_result.document.struct_data = None
    mock_result.chunk = MagicMock()
    mock_result.chunk.content = "Standard laptop refresh occurs every <b>3 years</b>."

    mock_response = MagicMock()
    mock_response.results = [mock_result]
    mock_client.search.return_value = mock_response

    with patch("enterprise_faq_agent.tools._get_search_client", return_value=mock_client):
        output = search_corporate_faq("When do I get a new laptop?")
        assert "Source 1: IT Hardware Policy" in output
        assert "Standard laptop refresh occurs every 3 years." in output
        assert "https://corp.internal/it/hardware" in output


def test_search_corporate_faq_deduplication(monkeypatch):
    monkeypatch.setenv("DISCOVERY_ENGINE_PROJECT_ID", "test-project")
    monkeypatch.setenv("DISCOVERY_ENGINE_ID", "corp-faq-engine")

    mock_client = MagicMock()

    mock_result = MagicMock()
    mock_result.chunk = None
    mock_result.document.derived_struct_data = {
        "title": "Duplicate Policy Excerpts",
        "extractive_segments": [
            {"content": "Employees must wear badge at all times."},
            {"content": "<b>Employees must wear badge at all times.</b>"},
        ],
    }
    mock_result.document.struct_data = None

    mock_response = MagicMock()
    mock_response.results = [mock_result]
    mock_client.search.return_value = mock_response

    with patch("enterprise_faq_agent.tools._get_search_client", return_value=mock_client):
        output = search_corporate_faq("Badge policy")
        assert output.count("Employees must wear badge at all times.") == 1


def test_search_corporate_faq_empty_results(monkeypatch):
    monkeypatch.setenv("DISCOVERY_ENGINE_PROJECT_ID", "test-project")
    monkeypatch.setenv("DISCOVERY_ENGINE_ID", "corp-faq-engine")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.results = []
    mock_client.search.return_value = mock_response

    with patch("enterprise_faq_agent.tools._get_search_client", return_value=mock_client):
        output = search_corporate_faq("Quantum teleportation reimbursement")
        assert "No relevant corporate FAQ documentation found" in output


def test_safe_get_helper():
    from enterprise_faq_agent.tools import _safe_get
    from google.cloud import discoveryengine_v1 as discoveryengine

    assert _safe_get({"title": "Test Title"}, "title") == "Test Title"
    assert _safe_get({"title": "Test Title"}, "nonexistent", "default") == "default"

    chunk = discoveryengine.Chunk()
    chunk.content = "Test content"
    chunk.document_metadata = {"title": "Doc From Chunk", "uri": "gs://chunk/doc.pdf"}
    assert _safe_get(chunk.document_metadata, "title") == "Doc From Chunk"
    assert _safe_get(chunk.document_metadata, "uri") == "gs://chunk/doc.pdf"

    assert _safe_get(None, "title", "fallback") == "fallback"


def test_search_corporate_faq_protobuf_structures(monkeypatch):
    from google.cloud import discoveryengine_v1 as discoveryengine

    monkeypatch.setenv("DISCOVERY_ENGINE_PROJECT_ID", "test-project")
    monkeypatch.setenv("DISCOVERY_ENGINE_LOCATION", "global")
    monkeypatch.setenv("DISCOVERY_ENGINE_ID", "corp-faq-engine")

    doc = discoveryengine.Document()
    doc.name = "projects/test-project/locations/global/collections/default_collection/engines/corp-faq-engine/documents/doc_proto"
    doc.derived_struct_data = {
        "title": "Corporate Travel & Expense Policy",
        "link": "https://corp.internal/policies/travel",
        "extractive_segments": [
            {"content": "Employees must submit expense reports within <b>30 days</b> of travel."},
        ],
    }

    proto_result = discoveryengine.SearchResponse.SearchResult(document=doc)
    proto_response = discoveryengine.SearchResponse(results=[proto_result])

    mock_client = MagicMock()
    mock_client.search.return_value = proto_response

    with patch("enterprise_faq_agent.tools._get_search_client", return_value=mock_client):
        output = search_corporate_faq("travel expenses")
        assert "Source 1: Corporate Travel & Expense Policy" in output
        assert "30 days of travel." in output
        assert "https://corp.internal/policies/travel" in output
