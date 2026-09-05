"""Application-wide logging configuration."""
import logging
import sys

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the root logger once and return the `app` logger.

    Should be called from ``app.main`` before anything else logs.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger("app")

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(handler)

    _CONFIGURED = True
    return logging.getLogger("app")


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger (automatically uses root config)."""
    return logging.getLogger(name)