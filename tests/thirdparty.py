import logging

logging.basicConfig(format="%[levelname] %(message)s")
logger = logging.getLogger(__name__)


def log_thirdparty():
    logger.setLevel(logging.INFO)
    logger.info("thirdparty-logging")
