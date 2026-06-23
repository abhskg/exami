import logging.config
import sys

from app.core.config import settings


def setup_logging() -> None:
    """
    Sets up the application's logging configuration using dictConfig.
    Standardizes log formats and controls verbose logging from external libraries.
    """
    log_level = settings.LOG_LEVEL.upper()

    # Configure logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            # Root application logger
            "app": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            # Uvicorn error/system loggers
            "uvicorn.error": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            # Uvicorn access loggers
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            # SQLAlchemy engine logs (warning by default to avoid query flooding)
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
        },
        # Fallback root logger configuration
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
    }

    logging.config.dictConfig(logging_config)
