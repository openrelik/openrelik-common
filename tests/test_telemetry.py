import json
from unittest.mock import MagicMock, patch

import pytest

from openrelik_common import telemetry


def test_is_enabled(monkeypatch):
    monkeypatch.delenv("OPENRELIK_OTEL_MODE", raising=False)
    assert not telemetry.is_enabled()

    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-grpc")
    assert telemetry.is_enabled()

    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-http")
    assert telemetry.is_enabled()

    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "something-else")
    assert not telemetry.is_enabled()


@patch("openrelik_common.telemetry.compute_engine._metadata.get_project_id")
def test_get_gcp_project_id(mock_get_project_id):
    mock_get_project_id.return_value = "my-project"
    assert telemetry._get_gcp_project_id() == "my-project"


@patch("openrelik_common.telemetry.compute_engine._metadata.get_project_id")
def test_get_gcp_project_id_error(mock_get_project_id):
    from google.auth import exceptions as auth_exceptions

    mock_get_project_id.side_effect = auth_exceptions.TransportError("error")
    assert telemetry._get_gcp_project_id() is None


@patch("openrelik_common.telemetry.trace.set_tracer_provider")
def test_setup_telemetry_disabled(mock_set_tracer, monkeypatch):
    monkeypatch.delenv("OPENRELIK_OTEL_MODE", raising=False)
    telemetry.setup_telemetry("test-service")
    mock_set_tracer.assert_not_called()


@patch("openrelik_common.telemetry.grpc_exporter.OTLPSpanExporter")
@patch("openrelik_common.telemetry.trace.set_tracer_provider")
@patch("openrelik_common.telemetry.TracerProvider")
@patch("openrelik_common.telemetry.BatchSpanProcessor")
def test_setup_telemetry_grpc(
    mock_bsp, mock_tp, mock_set_tracer, mock_grpc, monkeypatch
):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-grpc")
    monkeypatch.setenv("OPENRELIK_OTLP_GRPC_ENDPOINT", "test:4317")
    telemetry.setup_telemetry("test-service")
    mock_grpc.assert_called_once_with(endpoint="test:4317", insecure=True)
    mock_set_tracer.assert_called_once()


@patch("openrelik_common.telemetry.http_exporter.OTLPSpanExporter")
@patch("openrelik_common.telemetry.trace.set_tracer_provider")
@patch("openrelik_common.telemetry.TracerProvider")
@patch("openrelik_common.telemetry.BatchSpanProcessor")
def test_setup_telemetry_http(
    mock_bsp, mock_tp, mock_set_tracer, mock_http, monkeypatch
):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-http")
    monkeypatch.setenv("OPENRELIK_OTLP_HTTP_ENDPOINT", "http://test:4318/v1/traces")
    telemetry.setup_telemetry("test-service")
    mock_http.assert_called_once_with(endpoint="http://test:4318/v1/traces")
    mock_set_tracer.assert_called_once()


@patch("openrelik_common.telemetry.TraceServiceClient")
@patch("openrelik_common.telemetry.compute_engine.Credentials")
@patch("openrelik_common.telemetry._get_gcp_project_id", return_value="my-project")
@patch("openrelik_common.telemetry.cloud_trace.CloudTraceSpanExporter")
@patch("openrelik_common.telemetry.trace.set_tracer_provider")
@patch("openrelik_common.telemetry.TracerProvider")
@patch("openrelik_common.telemetry.BatchSpanProcessor")
def test_setup_telemetry_gce(
    mock_bsp,
    mock_tp,
    mock_set_tracer,
    mock_cloud,
    mock_get_project_id,
    mock_creds,
    mock_trace_client,
    monkeypatch,
):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-default-gce")
    telemetry.setup_telemetry("test-service")
    mock_cloud.assert_called()
    mock_set_tracer.assert_called_once()


@patch("openrelik_common.telemetry.CeleryInstrumentor")
def test_instrument_celery_app(mock_instrumentor, monkeypatch):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-grpc")
    mock_app = MagicMock()
    telemetry.instrument_celery_app(mock_app)
    mock_instrumentor.return_value.instrument.assert_called_once_with(
        celery_app=mock_app
    )


def test_instrument_celery_app_disabled(monkeypatch):
    monkeypatch.delenv("OPENRELIK_OTEL_MODE", raising=False)
    # Shouldn't error
    telemetry.instrument_celery_app(MagicMock())


@patch("openrelik_common.telemetry.FastAPIInstrumentor")
def test_instrument_fast_api(mock_instrumentor, monkeypatch):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-grpc")
    mock_app = MagicMock()
    telemetry.instrument_fast_api(mock_app)
    mock_instrumentor.instrument_app.assert_called_once_with(mock_app)


@patch("openrelik_common.telemetry.trace.get_current_span")
def test_add_event_to_current_span(mock_get_span, monkeypatch):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-grpc")
    mock_span = MagicMock()
    mock_get_span.return_value = mock_span

    telemetry.add_event_to_current_span("test-event")
    mock_span.add_event.assert_called_once_with("test-event")


@patch("openrelik_common.telemetry.trace.get_current_span")
def test_add_event_to_current_span_invalid_span(mock_get_span, monkeypatch):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-grpc")
    from opentelemetry.trace.span import INVALID_SPAN

    mock_get_span.return_value = INVALID_SPAN

    # Should not error or crash
    telemetry.add_event_to_current_span("test-event")


@patch("openrelik_common.telemetry.trace.get_current_span")
def test_add_attribute_to_current_span(mock_get_span, monkeypatch):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-grpc")
    mock_span = MagicMock()
    mock_get_span.return_value = mock_span

    telemetry.add_attribute_to_current_span("test-key", {"a": "b"})
    mock_span.set_attribute.assert_called_once_with("test-key", '{"a": "b"}')


@patch("openrelik_common.telemetry.trace.get_current_span")
def test_add_attribute_to_current_span_invalid_span(mock_get_span, monkeypatch):
    monkeypatch.setenv("OPENRELIK_OTEL_MODE", "otlp-grpc")
    from opentelemetry.trace.span import INVALID_SPAN

    mock_get_span.return_value = INVALID_SPAN

    telemetry.add_attribute_to_current_span("test-key", {"a": "b"})


def test_safe_telemetry_call_exception():
    @telemetry.safe_telemetry_call
    def crash_func():
        raise ValueError("crash")

    # Should not raise exception
    assert crash_func() is None
