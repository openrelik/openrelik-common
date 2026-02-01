import json
import logging
import os
import pytest_structlog
from openrelik_common.logging import Logger
from .thirdparty import log_thirdparty


# Log usage functions
def log_plain():
    os.environ.pop("OPENRELIK_LOG_TYPE", None)
    logger = Logger().get_logger(__name__)
    logger.info("test")


def log_wrap():
    os.environ.pop("OPENRELIK_LOG_TYPE", None)
    logger = Logger().get_logger(name=__name__, wrap_logger=logging.getLogger())
    logger.info("test")


def log_bind_structlog():
    os.environ["OPENRELIK_LOG_TYPE"] = "structlog"
    log = Logger()
    logger = log.get_logger(__name__)
    log.bind(workflow_id=12345)
    logger.info("test")


def log_structlog():
    os.environ["OPENRELIK_LOG_TYPE"] = "structlog"
    logger = Logger().get_logger(__name__)
    logger.info("test")


def log_bind_structlog_console():
    os.environ["OPENRELIK_LOG_TYPE"] = "structlog_console"
    log = Logger()
    logger = log.get_logger(__name__)
    log.bind(workflow_id=12345)
    logger.info("test")


def log_structlog_console():
    os.environ["OPENRELIK_LOG_TYPE"] = "structlog_console"
    logger = Logger().get_logger(__name__)
    logger.info("test")


def log_structlog_3rdparty():
    os.environ["OPENRELIK_LOG_TYPE"] = "structlog"
    Logger()
    log_thirdparty()


# Tests
def test_structlog(log: pytest_structlog.StructuredLogCapture):
    log_structlog()
    assert log.has("test", level="info")
    assert not log.has("bla", workflow_id=12345)


def test_bind_structlog(log: pytest_structlog.StructuredLogCapture):
    log_bind_structlog()
    assert log.has("test", level="info", workflow_id=12345)


def test_structlog_console(log: pytest_structlog.StructuredLogCapture):
    log_structlog_console()
    assert log.has("test", level="info")


def test_bind_structlog_console(log: pytest_structlog.StructuredLogCapture):
    log_bind_structlog_console()
    assert log.has("test", level="info", workflow_id=12345)


def test_get_plain_python(caplog):
    caplog.set_level(logging.INFO)
    log_plain()
    assert "INFO     tests.test_logging:test_logging.py:13 test\n" == caplog.text


def test_get_wrap(log: pytest_structlog.StructuredLogCapture):
    log_wrap()
    assert log.has("test", level="info")


def test_structlog_3rdparty(capsys):
    log_structlog_3rdparty()
    captured = capsys.readouterr()
    logobj = json.loads(captured.out)
    assert logobj["event"] == "thirdparty-logging"
    assert logobj["level"] == "info"
    # assert "xxxxx" == captured.out
