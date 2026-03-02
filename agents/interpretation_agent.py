"""Analytics Interpretation Agent: generates insights from Looker query results."""

from google.genai import types

from agents.base import BaseAgent
from core.telemetry import get_tracer
from models.schemas import AgentState, InterpretationResponse, KPISummary


class AnalyticsInterpretationAgent(BaseAgent):
    """Agent that interprets Looker data and produces natural language insights."""

    async def run(self, state: AgentState) -> AgentState:
        tracer = get_tracer()
        with tracer.start_as_current_span("interpretation_agent") as span:
            span.set_attribute("request_id", state.request_id)

            if state.looker_data is None:
                state.errors.append("No Looker data to interpret")
                return state

            config = types.GenerateContentConfig(temperature=0.3)
            data_str = str(state.looker_data[:20])  # Limit for context
            query_used = state.generated_query.query_content if state.generated_query else "N/A"

            prompt = f"""You are an analytics interpretation agent. Analyze the Looker query results and produce:
1. A natural language summary answering the user's question
2. Key KPI summaries (name, value, trend if applicable)
3. Any anomalies or notable patterns
4. Actionable recommendations

User question: "{state.user_query}"
Query used: {query_used}

Data (first 20 rows): {data_str}

Respond in a structured way. Be concise and data-driven. If the data is empty or mock, note that and provide a sample interpretation format."""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            text = ""
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text

            # Parse structured response into InterpretationResponse
            kpis: list[KPISummary] = []
            anomalies: list[str] = []
            recommendations: list[str] = []

            # Simple heuristic parsing - in production, use response_schema or JSON mode
            lines = text.split("\n")
            for line in lines:
                lower = line.lower()
                if "anomal" in lower or "unusual" in lower:
                    anomalies.append(line.strip())
                elif "recommend" in lower or "suggest" in lower:
                    recommendations.append(line.strip())

            state.interpretation = InterpretationResponse(
                natural_language_summary=text[:2000] if text else "No insights generated.",
                kpi_summaries=kpis,
                anomalies=anomalies[:5],
                recommendations=recommendations[:5],
            )

            self._update_token_usage(state, prompt, text)
        return state
