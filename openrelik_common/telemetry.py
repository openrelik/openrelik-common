# OpenRelik OpenTelemetry helper methods

import json
import os

from opentelemetry import trace

from opentelemetry.exporter.otlp.proto.grpc import trace_exporter as grpc_exporter
from opentelemetry.exporter.otlp.proto.http import trace_exporter as http_exporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def setup_telemetry(service_name: str):
    """Configures the OpenTelemetry trace exporter.

    Args:
        service_name (str): the service name used to identify generated traces.
    """

    resource = Resource(attributes={
        "service.name": service_name
    })

    # --- Tracing Setup ---
    trace.set_tracer_provider(TracerProvider(resource=resource))

    otel_mode = os.environ.get("OPENRELIK_OTEL_MODE", "otlp-grpc")
    otlp_grpc_endpoint = os.environ.get("OPENRELIK_OTLP_GRPC_ENDPOINT", "jaeger:4317")
    otlp_http_endpoint = os.environ.get("OPENRELIK_OTLP_HTTP_ENDPOINT", "http://jaeger:4318/v1/traces")

    trace_exporter = None
    if otel_mode == "otlp-grpc":
        trace_exporter = grpc_exporter.OTLPSpanExporter(
                endpoint=otlp_grpc_endpoint, insecure=True)
    elif otel_mode == "otlp-http":
        trace_exporter = http_exporter.OTLPSpanExporter(
                endpoint=otlp_http_endpoint)
    else:
        raise Exception("Unsupported OTEL tracing mode %s", otel_mode)

    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(trace_exporter))


def instrument_celery_app(celery_app):
    """Helper method to call the OpenTelemetry Python instrumentor on an Celery app object.

    Args:
        celery_app (celery.app.Celery): the celery app to instrument.
    """
    CeleryInstrumentor().instrument(celery_app=celery_app)


def add_attribute_to_current_span(name: str, value: object):
    """This methods tried to get a handle of the OpenTelemetry span in the current context, and add
    an attribute to it, using the name and value passed as arguments.

    Args:
        name (str): the name for the attribute.
        value (object): the value of the attribute. This needs to be a json serializable object.
    """
    otel_span = trace.get_current_span()
    if otel_span != trace.span.INVALID_SPAN:
        otel_span.set_attribute(name, json.dumps(value))
