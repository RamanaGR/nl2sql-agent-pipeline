"""Supervisor/Router: orchestrates Metadata, Query, and Interpretation agents."""

import uuid

from loguru import logger

from agents.interpretation_agent import AnalyticsInterpretationAgent
from agents.metadata_agent import MetadataDiscoveryAgent
from agents.query_agent import QueryGenerationAgent
from core.telemetry import get_tracer
from models.schemas import AgentState


class Supervisor:
    """Orchestrates the multi-agent pipeline: Metadata -> Query -> Interpretation."""

    def __init__(self) -> None:
        self.metadata_agent = MetadataDiscoveryAgent()
        self.query_agent = QueryGenerationAgent()
        self.interpretation_agent = AnalyticsInterpretationAgent()

    async def run(self, user_query: str, request_id: str | None = None) -> AgentState:
        """Execute the full agent pipeline and return final state."""
        request_id = request_id or str(uuid.uuid4())
        state = AgentState(request_id=request_id, user_query=user_query)

        tracer = get_tracer()
        with tracer.start_as_current_span("supervisor_orchestration") as span:
            span.set_attribute("request_id", request_id)
            span.set_attribute("user_query", user_query[:200])

            try:
                state = await self.metadata_agent.run(state)
                if state.errors:
                    logger.warning("Metadata agent errors: {}", state.errors)
                    return state

                state = await self.query_agent.run(state)
                if state.errors:
                    logger.warning("Query agent errors: {}", state.errors)
                    return state

                state = await self.interpretation_agent.run(state)
                logger.info(
                    "Pipeline complete for {} | tokens: {}",
                    request_id,
                    state.token_usage,
                )
            except Exception as e:
                state.errors.append(str(e))
                logger.exception("Pipeline failed for {}", request_id)

        return state
