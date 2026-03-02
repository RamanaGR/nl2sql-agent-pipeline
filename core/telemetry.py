"""OpenTelemetry tracing and token usage tracking."""

from functools import lru_cache

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from core.config import get_settings


def _setup_tracer_provider() -> TracerProvider:
    """Configure and return TracerProvider."""
    settings = get_settings()
    resource = Resource.create({"service.name": settings.service_name})
    provider = TracerProvider(resource=resource)

    if settings.otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        except ImportError:
            exporter = ConsoleSpanExporter()
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


@lru_cache
def _get_provider() -> TracerProvider:
    return _setup_tracer_provider()


def get_tracer() -> trace.Tracer:
    """Get configured tracer for the service."""
    settings = get_settings()
    _get_provider()
    return trace.get_tracer(settings.service_name, "1.0.0")
