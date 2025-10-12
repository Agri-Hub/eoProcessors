import logging
import pytest
from datetime import datetime


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure a shared logger for all tests."""
    log_dir = "logs"
    log_file = f"{log_dir}/test_run_{datetime.now():%Y%m%d_%H%M%S}.log"

    import os

    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.info(f"Logging initialized → {log_file}")
    yield
    logging.info("Logging session finished.")
