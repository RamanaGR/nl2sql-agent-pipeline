"""Tests for Looker tools."""

import pytest

from tools.looker_tools import (
    discover_metadata,
    get_explore_dimensions,
    get_explore_measures,
    get_lookml_models,
    run_inline_query,
)


class TestLookerTools:
    """Tests for Looker API tool functions."""

    def test_get_lookml_models_returns_list(self):
        """Without Looker credentials, returns mock model list."""
        result = get_lookml_models()
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "mock_model" in result

    def test_discover_metadata_returns_metadata_response(self):
        """discover_metadata returns valid MetadataResponse."""
        result = discover_metadata(model_name="mock_model")
        assert result.models
        assert result.explores
        assert result.raw_metadata.get("mock") is True

    def test_discover_metadata_with_explore(self):
        """discover_metadata with explore_name."""
        result = discover_metadata(
            model_name="mock_model",
            explore_name="orders",
        )
        assert any(e.name == "orders" for e in result.explores)

    def test_get_explore_dimensions(self):
        """get_explore_dimensions returns dimension list."""
        dims = get_explore_dimensions("mock_model", "orders")
        assert isinstance(dims, list)
        assert len(dims) >= 1

    def test_get_explore_measures(self):
        """get_explore_measures returns measure list."""
        measures = get_explore_measures("mock_model", "orders")
        assert isinstance(measures, list)
        assert len(measures) >= 1

    def test_run_inline_query_returns_list(self):
        """run_inline_query returns list of dicts (mock data)."""
        result = run_inline_query(
            model="mock_model",
            view="orders",
            fields=["orders.count", "orders.total_amount"],
        )
        assert isinstance(result, list)
        assert len(result) >= 1
        assert isinstance(result[0], dict)
