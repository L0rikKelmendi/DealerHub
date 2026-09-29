"""Structured application logging."""

import logging
import sys


class PropsFormatter(logging.Formatter):
    """Formats the ``props`` extra dict as key=value pairs."""

    def format(self, record: logging.LogRecord) -> str:
        props = getattr(record, "props", None)
        base = super().format(record)
        if props:
            extra = " ".join(f"{k}={v}" for k, v in props.items())
            return f"{base} {extra}"
        return base


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        PropsFormatter(
            "%(asctime)s %(levelname)-8s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).handlers = []
        logging.getLogger(noisy).propagate = True
