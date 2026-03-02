"""Strict Pydantic schemas for tool inputs, outputs, and agent state."""

from typing import Any

from pydantic import BaseModel, Field


# --- Metadata Discovery ---

class MetadataRequest(BaseModel):
    """Input for metadata discovery requests."""

    model_name: str = Field(..., description="LookML model name")
    explore_name: str | None = Field(
        default=None,
        description="Optional explore name to narrow scope",
    )
    include_dimensions: bool = Field(default=True, description="Include dimension metadata")
    include_measures: bool = Field(default=True, description="Include measure metadata")


class DimensionInfo(BaseModel):
    """Metadata for a LookML dimension."""

    name: str
    type: str
    description: str | None = None
    sql: str | None = None


class MeasureInfo(BaseModel):
    """Metadata for a LookML measure."""

    name: str
    type: str
    description: str | None = None
    sql: str | None = None


class ExploreInfo(BaseModel):
    """Metadata for a LookML explore."""

    name: str
    description: str | None = None
    dimensions: list[DimensionInfo] = Field(default_factory=list)
    measures: list[MeasureInfo] = Field(default_factory=list)


class MetadataResponse(BaseModel):
    """Response from metadata discovery."""

    models: list[str] = Field(default_factory=list)
    explores: list[ExploreInfo] = Field(default_factory=list)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


# --- Query Generation ---

class QueryRequest(BaseModel):
    """Input for query generation requests."""

    user_intent: str = Field(..., description="Natural language user query/intent")
    model_name: str = Field(..., description="LookML model name")
    explore_name: str = Field(..., description="Explore to query")
    dimensions: list[str] = Field(default_factory=list)
    measures: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=100, ge=1, le=5000)
    metadata_context: MetadataResponse | None = Field(
        default=None,
        description="Grounded metadata from discovery agent",
    )


class QueryResponse(BaseModel):
    """Response from query generation."""

    query_type: str = Field(..., description="'sql' | 'lookml' | 'api'")
    query_content: str = Field(..., description="Generated query or LookML")
    api_payload: dict[str, Any] | None = Field(
        default=None,
        description="Looker API request payload if query_type is 'api'",
    )
    rationale: str | None = Field(default=None, description="Generation rationale")


# --- Analytics Interpretation ---

class InterpretationRequest(BaseModel):
    """Input for analytics interpretation."""

    data_payload: list[dict[str, Any]] = Field(
        ...,
        description="Data rows from Looker query result",
    )
    original_query: str = Field(..., description="Original user question")
    query_used: str | None = Field(default=None, description="SQL/query that was executed")


class KPISummary(BaseModel):
    """KPI summary item."""

    name: str
    value: Any
    trend: str | None = None
    insight: str | None = None


class InterpretationResponse(BaseModel):
    """Response from analytics interpretation."""

    natural_language_summary: str = Field(..., description="Human-readable insights")
    kpi_summaries: list[KPISummary] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# --- Agent State (Supervisor/Router) ---

class AgentState(BaseModel):
    """Shared state passed between agents in orchestration."""

    request_id: str
    user_query: str
    metadata: MetadataResponse | None = None
    generated_query: QueryResponse | None = None
    looker_data: list[dict[str, Any]] | None = None
    interpretation: InterpretationResponse | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
