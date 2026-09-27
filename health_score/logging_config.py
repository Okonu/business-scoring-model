"""Logging setup shared by the API and the web page"""

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once; later calls only change the level"""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    root.setLevel(level.upper())
    # urllib3 logs every retry and pool event at WARNING
    logging.getLogger("urllib3").setLevel(logging.ERROR)
