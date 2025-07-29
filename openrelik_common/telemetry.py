"""
Module providing OpenTelemetry capability to other openrelik codebases.

Depending on whether your OpenTelemetry endpoint is configured to recieve traces
via GRPC or HTTP method, first set the OPENRELIK_OTEL_MODE environment variable
to either `otlp-grpc` or `otlp-http`.
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

import os

from opentelemetry import trace

from opentelemetry.exporter.otlp.proto.grpc import trace_exporter as grpc_exporter
from opentelemetry.exporter.otlp.proto.http import trace_exporter as http_exporter
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
