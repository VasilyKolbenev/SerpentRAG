"""
OpenTelemetry and Prometheus instrumentation.
"""

import logging

from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger("serpent.telemetry")


def setup_telemetry(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing and Prometheus metrics."""
    # Prometheus metrics
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/readyz", "/metrics"],
        ).instrument(app).expose(app, include_in_schema=False)

        logger.info("Prometheus metrics enabled")
    except ImportError:
        logger.warning("prometheus-fastapi-instrumentator not available")

    # OpenTelemetry
    if settings.is_production:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create({"service.name": "serpent-rag"})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)

            FastAPIInstrumentor.instrument_app(app)
            logger.info("OpenTelemetry tracing enabled")
        except ImportError:
            logger.warning("OpenTelemetry packages not available")
