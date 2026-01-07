"""
Module providing OpenTelemetry capability to other openrelik codebases.

Depending on whether your OpenTelemetry endpoint is configured to recieve traces
via GRPC or HTTP method, first set the OPENRELIK_OTEL_MODE environment variable
to either `otlp-grpc` or `otlp-http`.

Failure to set this environment variable means none of the following methods will
do anything.

Then you can configure the OpenRelik endpoint address by setting the environment
variable OPENRELIK_OTLP_GRPC_ENDPOINT or OPENRELIK_OTLP_HTTP_ENDPOINT, depending on
your usecase.

Example usage in a openrelik-worker codebase:
    In src/app.py:
    ```
       from openrelik_common import telemetry

       telemetry.setup_telemetry('openrelik-worker-strings')

       celery = Celery(...)

       telemetry.instrument_celery_app(celery)
    ```

    In src/tasks.py:
    ```
       from openrelik_comon import telemetry

       @celery.task(bind=True, name=TASK_NAME, metadata=TASK_METADATA)
       def strings(...):

         <...>

         telemetry.add_attribute_to_current_span("task_config", task_config)
    ```
"""
import json
import os

from opentelemetry import trace
from opentelemetry.trace.span import INVALID_SPAN

from opentelemetry.exporter import cloud_trace
from opentelemetry.exporter.otlp.proto.grpc import trace_exporter as grpc_exporter
from opentelemetry.exporter.otlp.proto.http import trace_exporter as http_exporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(service_name: str):
    """Configures the OpenTelemetry trace exporter.

    No-op if the environment variable OPENRELIK_OTEL_MODE is different from
    one of the two supported mode:
      - 'otel-default-gce', when exporting Google Cloud trace API,
            from a GCE instance.
      - 'otel-grpc', to export to an OpenTelemetry collector with gRPC
      - 'otel-http', to export to an OpenTelemetry collector with HTTP

    Args:
        service_name (str): the service name used to identify generated traces.
    """
    otel_mode = os.environ.get("OPENRELIK_OTEL_MODE", "")
    if not otel_mode.startswith("otlp-"):
        return

    resource = Resource(attributes={"service.name": service_name})

    trace_exporter = None
    if otel_mode == "otlp-grpc":
        otlp_grpc_endpoint = os.environ.get("OPENRELIK_OTLP_GRPC_ENDPOINT", "jaeger:4317")
        trace_exporter = grpc_exporter.OTLPSpanExporter(
            endpoint=otlp_grpc_endpoint, insecure=True
        )
    elif otel_mode == "otlp-http":
        otlp_http_endpoint = os.environ.get(
            "OPENRELIK_OTLP_HTTP_ENDPOINT", "http://jaeger:4318/v1/traces"
        )
        trace_exporter = http_exporter.OTLPSpanExporter(endpoint=otlp_http_endpoint)
    elif otel_mode == "default_gce":
        trace_exporter = cloud_trace.CloudTraceSpanExporter()
    else:
        raise Exception("Unsupported OTEL tracing mode %s", otel_mode)

    # --- Tracing Setup ---
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)


def instrument_celery_app(celery_app):
    """Helper method to call the OpenTelemetry Python instrumentor on an Celery app object.

    Args:
        celery_app (celery.app.Celery): the celery app to instrument.
    """
    otel_mode = os.environ.get("OPENRELIK_OTEL_MODE", "")
    if not otel_mode.startswith("otlp-"):
        return

    CeleryInstrumentor().instrument(celery_app=celery_app)


def instrument_fast_api(fast_api):
    """Helper method to call the OpenTelemetry Python instrumentor on an FastAPI app object.

    Args:
        fast_api (fastapi.FastAPI): the FastAPI app to instrument.
    """
    otel_mode = os.environ.get("OPENRELIK_OTEL_MODE", "")
    if not otel_mode.startswith("otlp-"):
        return

    FastAPIInstrumentor.instrument_app(fast_api)

def add_event_to_current_span(event: str):
    """Adds an OpenTelemetry event to the current span.

    Args:
        event (str): the message to add to the event.
    """
    otel_mode = os.environ.get("OPENRELIK_OTEL_MODE", "")
    if not otel_mode.startswith("otlp-"):
        return

    otel_span = trace.get_current_span()
    if otel_span != INVALID_SPAN:
        otel_span.add_event(event)


def add_attribute_to_current_span(name: str, value: object):
    """This methods tries to get a handle of the OpenTelemetry span in the current context, and add
    an attribute to it, using the name and value passed as arguments.

    Args:
        name (str): the name for the attribute.
        value (object): the value of the attribute. This needs to be a json serializable object.
    """
    otel_mode = os.environ.get("OPENRELIK_OTEL_MODE", "")
    if not otel_mode.startswith("otlp-"):
        return

    otel_span = trace.get_current_span()
    if otel_span != INVALID_SPAN:
        otel_span.set_attribute(name, json.dumps(value))
