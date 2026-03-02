"""Query Generation Agent: generates LookML/SQL/API queries from grounded metadata."""

from google.genai import types

from agents.base import BaseAgent
from core.telemetry import get_tracer
from models.schemas import AgentState, QueryResponse
from tools.looker_tools import run_inline_query

# Tool schema for query execution
RUN_QUERY_SCHEMA = {
    "name": "run_inline_query",
    "description": "Execute an inline query against Looker. Use after generating the query structure.",
    "parameters": {
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "LookML model name"},
            "view": {"type": "string", "description": "View (explore) name"},
            "fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fields to select (e.g., ['orders.count', 'orders.total_amount'])",
            },
            "filters": {
                "type": "object",
                "description": "Filter values as key-value pairs",
            },
            "limit": {"type": "integer", "description": "Row limit", "default": 100},
        },
        "required": ["model", "view", "fields"],
    },
}


class QueryGenerationAgent(BaseAgent):
    """Agent that generates LookML/SQL/API queries from user intent and metadata."""

    async def run(self, state: AgentState) -> AgentState:
        tracer = get_tracer()
        with tracer.start_as_current_span("query_generation_agent") as span:
            span.set_attribute("request_id", state.request_id)

            if state.metadata is None:
                state.errors.append("Metadata not available; run MetadataDiscoveryAgent first")
                return state

            tools = [
                types.Tool(function_declarations=[
                    types.FunctionDeclaration(
                        name="run_inline_query",
                        description=RUN_QUERY_SCHEMA["description"],
                        parameters=RUN_QUERY_SCHEMA["parameters"],
                    )
                ])
            ]
            config = types.GenerateContentConfig(tools=tools, temperature=0.2)

            meta_str = state.metadata.model_dump_json(indent=2)
            prompt = f"""You are a Looker query generation agent. Generate a valid Looker inline query for the user's request.

User query: "{state.user_query}"

Available metadata (use ONLY these fields - do not hallucinate):
{meta_str}

Determine the correct model, view (explore), and fields. Call run_inline_query with the appropriate parameters.
Use snake_case for field names (e.g., orders.count, orders.created_date)."""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            query_response: QueryResponse | None = None
            looker_data: list[dict] | None = None

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        if fc.name == "run_inline_query":
                            args = dict(fc.args) if fc.args else {}
                            model = args.get("model", "mock_model")
                            view = args.get("view", "orders")
                            fields = args.get("fields", ["orders.count", "orders.total_amount"])
                            filters = args.get("filters") or {}
                            limit = int(args.get("limit", 100))
                            looker_data = run_inline_query(
                                model=model,
                                view=view,
                                fields=fields,
                                filters=filters,
                                limit=limit,
                            )
                            query_response = QueryResponse(
                                query_type="api",
                                query_content=f"run_inline_query(model={model}, view={view}, fields={fields})",
                                api_payload=args,
                                rationale="Generated from user intent and metadata",
                            )
                            break

            if query_response is None:
                # Fallback: generate a synthetic query without execution
                explores = state.metadata.explores
                exp = explores[0] if explores else None
                model = state.metadata.models[0] if state.metadata.models else "mock_model"
                view = exp.name if exp else "orders"
                fields = [d.name for d in (exp.dimensions[:2] if exp else [])] + [
                    m.name for m in (exp.measures[:2] if exp else [])
                ]
                if not fields:
                    fields = ["orders.count", "orders.total_amount"]
                looker_data = run_inline_query(model=model, view=view, fields=fields)
                query_response = QueryResponse(
                    query_type="api",
                    query_content=f"run_inline_query(model={model}, view={view}, fields={fields})",
                    api_payload={"model": model, "view": view, "fields": fields},
                )

            state.generated_query = query_response
            state.looker_data = looker_data
            self._update_token_usage(state, prompt, str(response))
        return state
