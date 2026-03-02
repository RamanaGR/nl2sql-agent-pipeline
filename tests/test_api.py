"""Tests for FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create test client with cleared config cache."""
    from core.config import get_settings
    get_settings.cache_clear()
    from api.main import app
    return TestClient(app)


@pytest.fixture
def mock_supervisor_state():
    """Mock AgentState returned by Supervisor.run."""
    from models.schemas import AgentState, InterpretationResponse, MetadataResponse, QueryResponse
    return AgentState(
        request_id="test-req-123",
        user_query="What is revenue?",
        metadata=MetadataResponse(models=["mock"], explores=[]),
        generated_query=QueryResponse(query_type="api", query_content="mock"),
        looker_data=[{"count": 100}],
        interpretation=InterpretationResponse(
            natural_language_summary="Revenue is $50k",
            kpi_summaries=[],
            anomalies=[],
            recommendations=[],
        ),
        token_usage={"prompt_tokens": 10, "completion_tokens": 20},
        errors=[],
    )


class TestHealthEndpoint:
    """Tests for health check."""

    def test_health_returns_ok(self, api_client: TestClient):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestQueryEndpoint:
    """Tests for /api/v1/query endpoint."""

    def test_query_requires_body(self, api_client: TestClient):
        resp = api_client.post("/api/v1/query", json={})
        assert resp.status_code == 422  # validation error - query required

    def test_query_returns_200_with_mock(self, api_client: TestClient, mock_supervisor_state):
        """When supervisor is mocked, returns 200 with expected structure."""
        async def mock_run(query: str, request_id: str | None = None):
            return mock_supervisor_state

        with patch("api.routes.Supervisor") as MockSupervisor:
            MockSupervisor.return_value.run = AsyncMock(side_effect=mock_run)
            resp = api_client.post(
                "/api/v1/query",
                json={"query": "What is total order count?"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "request_id" in data
        assert "summary" in data
        assert data["request_id"] == "test-req-123"
        assert "Revenue" in data["summary"] or "50k" in data["summary"]


class TestAsyncQueryEndpoint:
    """Tests for /api/v1/query/async."""

    def test_async_query_returns_accepted(self, api_client: TestClient):
        resp = api_client.post(
            "/api/v1/query/async",
            json={"query": "What is revenue?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert "request_id" in data
