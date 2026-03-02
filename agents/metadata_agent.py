"""Metadata Discovery Agent: queries Looker metadata to ground LLM context."""

from google.genai import types

from agents.base import BaseAgent
from core.telemetry import get_tracer
from models.schemas import AgentState, MetadataResponse
from tools.looker_tools import discover_metadata

# Tool schema for Gemini function calling
DISCOVER_METADATA_SCHEMA = {
    "name": "discover_metadata",
    "description": "Query Looker metadata for models, explores, dimensions, and measures. Use this to ground your context and prevent hallucinations about available data.",
    "parameters": {
        "type": "object",
        "properties": {
            "model_name": {"type": "string", "description": "LookML model name"},
            "explore_name": {
                "type": "string",
                "description": "Optional explore name to narrow scope",
            },
            "include_dimensions": {
                "type": "boolean",
                "description": "Include dimension metadata",
                "default": True,
            },
            "include_measures": {
                "type": "boolean",
                "description": "Include measure metadata",
                "default": True,
            },
        },
        "required": ["model_name"],
    },
}


def _call_discover_metadata(
    model_name: str,
    explore_name: str | None = None,
    include_dimensions: bool = True,
    include_measures: bool = True,
) -> dict:
    """Tool implementation for discover_metadata. Returns JSON-serializable dict."""
    result = discover_metadata(
        model_name=model_name,
        explore_name=explore_name,
        include_dimensions=include_dimensions,
        include_measures=include_measures,
    )
    return result.model_dump()


class MetadataDiscoveryAgent(BaseAgent):
    """Agent that introspects Looker metadata to ground query generation."""

    def _get_tools(self) -> list[types.Tool]:
        declarations = [types.FunctionDeclaration(
            name="discover_metadata",
            description=DISCOVER_METADATA_SCHEMA["description"],
            parameters=DISCOVER_METADATA_SCHEMA["parameters"],
        )]
        return [types.Tool(function_declarations=declarations)]

    async def run(self, state: AgentState) -> AgentState:
        tracer = get_tracer()
        with tracer.start_as_current_span("metadata_discovery_agent") as span:
            span.set_attribute("request_id", state.request_id)

            tools = self._get_tools()
            config = types.GenerateContentConfig(
                tools=tools,
                temperature=0.1,
            )

            prompt = f"""You are a Looker metadata discovery agent. The user asked: "{state.user_query}"

Identify which LookML model and explore are likely relevant. If the user did not specify, infer from context (e.g., "orders" -> orders explore, "revenue" -> often in orders or similar).

Call discover_metadata with the appropriate model_name and optionally explore_name. Return the metadata you discover."""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            # Handle function call in response
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        if fc.name == "discover_metadata":
                            args = dict(fc.args) if fc.args else {}
                            metadata = discover_metadata(
                                model_name=args.get("model_name", "unknown"),
                                explore_name=args.get("explore_name"),
                                include_dimensions=args.get("include_dimensions", True),
                                include_measures=args.get("include_measures", True),
                            )
                            state.metadata = metadata
                            break

            if state.metadata is None:
                # Fallback: try common model/explore
                state.metadata = discover_metadata(
                    model_name="thelook" if "look" in state.user_query.lower() else "mock_model",
                    explore_name="orders",
                )

            self._update_token_usage(
                state, prompt, str(response)
            )
        return state
