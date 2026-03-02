"""REST API routes for agent workflows."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from agents.supervisor import Supervisor

router = APIRouter()


class QueryRequest(BaseModel):
    """Request body for natural language analytics query."""

    query: str = Field(..., description="Natural language question or KPI request")
    request_id: str | None = Field(default=None, description="Optional request ID for tracing")


class QueryResponse(BaseModel):
    """Response from analytics pipeline."""

    request_id: str
    summary: str
    kpis: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


async def _run_pipeline_task(query: str, request_id: str | None) -> None:
    """Background task to run the full agent pipeline."""
    supervisor = Supervisor()
    state = await supervisor.run(query, request_id)
    # Log completion; in production, you might push to Redis or notify
    from loguru import logger
    logger.info(
        "Pipeline completed: request_id={} errors={}",
        state.request_id,
        state.errors,
    )


@router.post("/query", response_model=QueryResponse)
async def run_query(
    body: QueryRequest,
    background_tasks: BackgroundTasks,
) -> QueryResponse:
    """
    Execute the full agent pipeline: Metadata -> Query -> Interpretation.
    Uses BackgroundTasks to simulate async event-driven KPI reporting.
    """
    supervisor = Supervisor()
    state = await supervisor.run(body.query, body.request_id)

    interpretation = state.interpretation
    summary = (
        interpretation.natural_language_summary
        if interpretation
        else "No interpretation available."
    )
    kpis = [k.model_dump() for k in (interpretation.kpi_summaries or [])]
    anomalies = interpretation.anomalies if interpretation else []
    recs = interpretation.recommendations if interpretation else []

    return QueryResponse(
        request_id=state.request_id,
        summary=summary,
        kpis=kpis,
        anomalies=anomalies,
        recommendations=recs,
        token_usage=state.token_usage,
        errors=state.errors,
    )


@router.post("/query/async")
async def run_query_async(
    body: QueryRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """
    Trigger the pipeline in the background. Returns immediately with request_id.
    Simulates event-driven async reporting.
    """
    import uuid
    request_id = body.request_id or str(uuid.uuid4())
    background_tasks.add_task(_run_pipeline_task, body.query, request_id)
    return {
        "status": "accepted",
        "request_id": request_id,
        "message": "Pipeline running in background. Poll status or use webhooks in production.",
    }
