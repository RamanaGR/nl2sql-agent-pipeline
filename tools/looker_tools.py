"""Looker 4.0 API wrappers for metadata introspection and query execution."""

import json
import os
from typing import Any

from loguru import logger

from core.config import get_settings
from models.schemas import (
    DimensionInfo,
    ExploreInfo,
    MeasureInfo,
    MetadataResponse,
)

# Retry configuration
MAX_RETRIES = 3


def _get_looker_client() -> Any:
    """Get authenticated Looker SDK client. Uses env vars from pydantic-settings."""
    try:
        from looker_sdk import init40

        settings = get_settings()
        if not settings.looker_client_id or not settings.looker_client_secret:
            return None

        # Looker SDK reads LOOKERSDK_* env vars
        os.environ["LOOKERSDK_BASE_URL"] = settings.looker_base_url
        os.environ["LOOKERSDK_CLIENT_ID"] = settings.looker_client_id
        os.environ["LOOKERSDK_CLIENT_SECRET"] = settings.looker_client_secret
        os.environ["LOOKERSDK_VERIFY_SSL"] = str(settings.looker_verify_ssl).lower()

        return init40()
    except Exception as e:
        logger.warning("Looker SDK init failed: {}", e)
        return None


def _mock_metadata_response(model_name: str, explore_name: str | None) -> MetadataResponse:
    """Return mock metadata when Looker is unavailable."""
    explore = ExploreInfo(
        name=explore_name or "orders",
        description="Mock explore for local development",
        dimensions=[
            DimensionInfo(name="orders.id", type="number", description="Order ID"),
            DimensionInfo(name="orders.created_date", type="date", description="Order date"),
            DimensionInfo(name="orders.status", type="string", description="Order status"),
        ],
        measures=[
            MeasureInfo(name="orders.count", type="count", description="Number of orders"),
            MeasureInfo(name="orders.total_amount", type="sum", description="Total order value"),
        ],
    )
    return MetadataResponse(
        models=["mock_model"],
        explores=[explore],
        raw_metadata={"mock": True},
    )


def _mock_query_result() -> list[dict[str, Any]]:
    """Return mock query result when Looker is unavailable."""
    return [
        {"orders.count": 150, "orders.total_amount": 45000.00},
        {"orders.count": 200, "orders.total_amount": 62000.00},
    ]


def get_lookml_models() -> list[str]:
    """Fetch all LookML model names from Looker."""
    for attempt in range(MAX_RETRIES):
        try:
            sdk = _get_looker_client()
            if sdk is None:
                return ["mock_model"]
            models = sdk.all_lookml_models()
            return [m.name for m in models] if models else ["mock_model"]
        except Exception as e:
            logger.warning("get_lookml_models attempt {} failed: {}", attempt + 1, e)
    return ["mock_model"]


def get_lookml_model_explore(model_name: str, explore_name: str) -> dict[str, Any]:
    """Get explore metadata for a given model and explore."""
    for attempt in range(MAX_RETRIES):
        try:
            sdk = _get_looker_client()
            if sdk is None:
                return {"name": explore_name, "description": "Mock explore", "fields": []}
            explore = sdk.lookml_model_explore(model_name, explore_name)
            return explore.__dict__ if hasattr(explore, "__dict__") else {"name": explore_name}
        except Exception as e:
            logger.warning("get_lookml_model_explore attempt {} failed: {}", attempt + 1, e)
    return {"name": explore_name, "description": "Mock explore", "fields": []}


def get_explore_dimensions(model_name: str, explore_name: str) -> list[DimensionInfo]:
    """Extract dimension metadata from an explore."""
    raw = get_lookml_model_explore(model_name, explore_name)
    dims: list[DimensionInfo] = []
    if "fields" in raw and "dimensions" in raw["fields"]:
        for d in raw["fields"]["dimensions"]:
            dims.append(
                DimensionInfo(
                    name=d.get("name", ""),
                    type=d.get("type", "string"),
                    description=d.get("description"),
                    sql=d.get("sql"),
                )
            )
    if not dims:
        dims = [
            DimensionInfo(name="id", type="number"),
            DimensionInfo(name="created_date", type="date"),
        ]
    return dims


def get_explore_measures(model_name: str, explore_name: str) -> list[MeasureInfo]:
    """Extract measure metadata from an explore."""
    raw = get_lookml_model_explore(model_name, explore_name)
    measures: list[MeasureInfo] = []
    if "fields" in raw and "measures" in raw["fields"]:
        for m in raw["fields"]["measures"]:
            measures.append(
                MeasureInfo(
                    name=m.get("name", ""),
                    type=m.get("type", "count"),
                    description=m.get("description"),
                    sql=m.get("sql"),
                )
            )
    if not measures:
        measures = [
            MeasureInfo(name="count", type="count"),
            MeasureInfo(name="total_amount", type="sum"),
        ]
    return measures


def discover_metadata(
    model_name: str,
    explore_name: str | None = None,
    include_dimensions: bool = True,
    include_measures: bool = True,
) -> MetadataResponse:
    """
    Dynamic schema introspection: query Looker metadata for models, explores, dimensions, measures.
    Returns mock data if Looker credentials are not configured.
    """
    sdk = _get_looker_client()
    if sdk is None:
        return _mock_metadata_response(model_name, explore_name)

    try:
        models = get_lookml_models()
        explores: list[ExploreInfo] = []

        # If explore_name specified, fetch that explore only
        if explore_name:
            dims = get_explore_dimensions(model_name, explore_name) if include_dimensions else []
            meas = get_explore_measures(model_name, explore_name) if include_measures else []
            explores.append(
                ExploreInfo(
                    name=explore_name,
                    dimensions=dims,
                    measures=meas,
                )
            )
        else:
            # Fetch all explores for the model
            explore_list = []
            try:
                model_detail = sdk.lookml_model(model_name)
                if hasattr(model_detail, "explores") and model_detail.explores:
                    explore_list = [e.get("name", e) if isinstance(e, dict) else str(e) for e in model_detail.explores]
            except Exception:
                explore_list = ["orders", "users"]

            for exp_name in explore_list[:5]:  # Limit to 5 explores
                dims = get_explore_dimensions(model_name, exp_name) if include_dimensions else []
                meas = get_explore_measures(model_name, exp_name) if include_measures else []
                explores.append(ExploreInfo(name=exp_name, dimensions=dims, measures=meas))

        return MetadataResponse(models=models, explores=explores)
    except Exception as e:
        logger.warning("discover_metadata failed, returning mock: {}", e)
        return _mock_metadata_response(model_name, explore_name)


def run_inline_query(
    model: str,
    view: str,
    fields: list[str],
    filters: dict[str, str] | None = None,
    limit: int = 100,
    result_format: str = "json",
) -> list[dict[str, Any]]:
    """
    Execute an inline query against Looker 4.0 API.
    Returns mock data if Looker is unavailable.
    """
    sdk = _get_looker_client()
    if sdk is None:
        return _mock_query_result()

    try:
        from looker_sdk import models40 as models

        body = models.WriteQuery(
            model=model,
            view=view,
            fields=fields,
            filters=filters or {},
            limit=limit,
        )
        result = sdk.run_inline_query(result_format=result_format, body=body, cache=False)
        if isinstance(result, bytes):
            return json.loads(result.decode())
        if isinstance(result, str):
            return json.loads(result)
        return list(result) if result else []
    except Exception as e:
        logger.warning("run_inline_query failed, returning mock: {}", e)
        return _mock_query_result()
