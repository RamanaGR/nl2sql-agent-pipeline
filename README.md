# NL2SQL Agent Pipeline

A production-ready, event-driven multi-agent analytics platform that translates natural language into Looker API/LookML queries using a Supervisor/Router orchestration pattern.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| AI | Google Gemini API (`google-genai` SDK) |
| API | FastAPI |
| BI/Data | Looker 4.0 API (`looker-sdk`) |
| Validation | Pydantic V2 |
| Async | FastAPI BackgroundTasks, Redis/Celery |
| Observability | OpenTelemetry, Loguru |
| Deployment | Docker Compose |

## Project Structure

```
nl2sql-agent-pipeline/
├── agents/
│   ├── __init__.py
│   ├── base.py              # Base agent with Gemini client
│   ├── metadata_agent.py    # Metadata Discovery Agent
│   ├── query_agent.py       # Query Generation Agent
│   ├── interpretation_agent.py  # Analytics Interpretation Agent
│   └── supervisor.py        # Orchestrator (Metadata → Query → Interpretation)
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + telemetry
│   └── routes.py            # REST endpoints
├── core/
│   ├── __init__.py
│   ├── config.py            # Pydantic-settings from .env
│   └── telemetry.py         # OpenTelemetry tracing
├── models/
│   ├── __init__.py
│   └── schemas.py           # Pydantic models for tools & state
├── tools/
│   ├── __init__.py
│   └── looker_tools.py      # Looker 4.0 API wrappers
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── run.py                   # Local uvicorn entrypoint
```

## Multi-Agent Architecture

1. **Metadata Discovery Agent** – Introspects Looker models, explores, dimensions, and measures via dynamic schema tools. Grounds the LLM to prevent hallucinations.

2. **Query Generation Agent** – Takes grounded metadata and user intent to generate Looker inline queries. Uses native function calling to invoke `run_inline_query`.

3. **Analytics Interpretation Agent** – Interprets Looker query results and produces natural language insights, KPI summaries, anomaly detection, and recommendations.

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY (required)
# Optionally set Looker credentials for live Looker; otherwise mock data is used
```

### 2. Local development

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python run.py
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

### 3. Run tests

```bash
pytest tests/ -v
```

### 4. Docker

```bash
docker-compose up --build
```

### 5. Example request

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the total order count and revenue?"}'
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/query` | Run full pipeline (sync) |
| POST | `/api/v1/query/async` | Trigger pipeline in background |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `LOOKER_BASE_URL` | No | Looker instance URL |
| `LOOKER_CLIENT_ID` | No | Looker API client ID |
| `LOOKER_CLIENT_SECRET` | No | Looker API client secret |
| `OTLP_ENDPOINT` | No | OpenTelemetry endpoint |
| `REDIS_URL` | No | Redis URL for Celery/events |

## Observability

- **OpenTelemetry** traces agent reasoning loops (routing, tool calls, generation)
- **Loguru** for structured logging
- Token usage logged per request
- Optional Jaeger for trace visualization (included in docker-compose)

## License

MIT
