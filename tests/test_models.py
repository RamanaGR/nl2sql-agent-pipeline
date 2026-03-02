"""Tests for Pydantic models/schemas."""

import pytest

from models.schemas import (
    AgentState,
    DimensionInfo,
    ExploreInfo,
    InterpretationResponse,
    KPISummary,
    MeasureInfo,
    MetadataRequest,
    MetadataResponse,
    QueryRequest,
    QueryResponse,
)


class TestMetadataSchemas:
    """Tests for metadata-related schemas."""

    def test_metadata_request_minimal(self):
        req = MetadataRequest(model_name="thelook")
        assert req.model_name == "thelook"
        assert req.explore_name is None
        assert req.include_dimensions is True
        assert req.include_measures is True

    def test_metadata_request_full(self):
        req = MetadataRequest(
            model_name="thelook",
            explore_name="orders",
            include_dimensions=False,
            include_measures=True,
        )
        assert req.explore_name == "orders"
        assert req.include_dimensions is False

    def test_dimension_info(self):
        d = DimensionInfo(name="orders.id", type="number", description="Order ID")
        assert d.name == "orders.id"
        assert d.type == "number"
        assert d.sql is None

    def test_measure_info(self):
        m = MeasureInfo(name="orders.count", type="count")
        assert m.name == "orders.count"
        assert m.type == "count"

    def test_explore_info(self):
        exp = ExploreInfo(
            name="orders",
            dimensions=[DimensionInfo(name="id", type="number")],
            measures=[MeasureInfo(name="count", type="count")],
        )
        assert exp.name == "orders"
        assert len(exp.dimensions) == 1
        assert len(exp.measures) == 1

    def test_metadata_response(self):
        resp = MetadataResponse(models=["m1"], explores=[], raw_metadata={"k": "v"})
        assert resp.models == ["m1"]
        assert resp.raw_metadata == {"k": "v"}


class TestQuerySchemas:
    """Tests for query-related schemas."""

    def test_query_request(self):
        req = QueryRequest(
            user_intent="total revenue",
            model_name="thelook",
            explore_name="orders",
        )
        assert req.user_intent == "total revenue"
        assert req.limit == 100

    def test_query_request_limit_validation(self):
        req = QueryRequest(
            user_intent="x",
            model_name="m",
            explore_name="e",
            limit=50,
        )
        assert req.limit == 50

    def test_query_response(self):
        resp = QueryResponse(
            query_type="api",
            query_content="run_inline_query(...)",
            api_payload={"model": "m", "view": "v"},
        )
        assert resp.query_type == "api"
        assert resp.api_payload["model"] == "m"


class TestInterpretationSchemas:
    """Tests for interpretation schemas."""

    def test_kpi_summary(self):
        kpi = KPISummary(name="Revenue", value=1000, trend="up", insight="Growing")
        assert kpi.name == "Revenue"
        assert kpi.value == 1000
        assert kpi.trend == "up"

    def test_interpretation_response(self):
        resp = InterpretationResponse(
            natural_language_summary="Total revenue is $50k",
            kpi_summaries=[KPISummary(name="Revenue", value=50000)],
            anomalies=["Spike in Q3"],
            recommendations=["Monitor trend"],
        )
        assert "50k" in resp.natural_language_summary
        assert len(resp.kpi_summaries) == 1
        assert len(resp.anomalies) == 1


class TestAgentState:
    """Tests for AgentState schema."""

    def test_agent_state_minimal(self):
        state = AgentState(request_id="req-1", user_query="What is revenue?")
        assert state.request_id == "req-1"
        assert state.user_query == "What is revenue?"
        assert state.metadata is None
        assert state.errors == []

    def test_agent_state_with_metadata(self):
        meta = MetadataResponse(models=["m1"])
        state = AgentState(
            request_id="req-1",
            user_query="x",
            metadata=meta,
        )
        assert state.metadata is not None
        assert state.metadata.models == ["m1"]
