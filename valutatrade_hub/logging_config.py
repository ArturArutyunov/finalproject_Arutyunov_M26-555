import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from .constants import (
    LOG_BACKUP_COUNT_DEFAULT,
    LOG_FILE_DEFAULT,
    LOG_FILE_SIZE_DEFAULT,
    LOG_ROTATION_DEFAULT,
    PARSER_LOG_FILE_DEFAULT,
)
from .infra.settings import BASE_DIR, SettingsLoader

_LOGGER_NAME = "valutatrade"
_LOGGER_PARSER_NAME = "valutatrade.parser"
_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

_configured = set()


def _configure(logger_name, file_key, level_key, default_file, default_level):
    if logger_name in _configured:
        return
    settings = SettingsLoader()

    level_name = settings.get(level_key, default_level).upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = settings.get("log_format", _DEFAULT_FORMAT)
    log_file = BASE_DIR / settings.get(file_key, default_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    rotation = settings.get("log_rotation", LOG_ROTATION_DEFAULT)
    backup_count = settings.get("log_backup_count", LOG_BACKUP_COUNT_DEFAULT)

    if rotation == "size":
        file_size = settings.get("log_file_size", LOG_FILE_SIZE_DEFAULT)
        handler = RotatingFileHandler(
            log_file, maxBytes=file_size,
            backupCount=backup_count, encoding="utf-8",
        )
    else:
        handler = TimedRotatingFileHandler(
            log_file, when="midnight",
            backupCount=backup_count, encoding="utf-8",
        )

    handler.setFormatter(logging.Formatter(log_format))

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(handler)
    _configured.add(logger_name)


def setup_logging():
    _configure(_LOGGER_NAME, "log_file", "log_level", LOG_FILE_DEFAULT, "INFO")


def setup_parser_logging():
    _configure(
        _LOGGER_PARSER_NAME, "parser_log_file", "parser_log_level",
        PARSER_LOG_FILE_DEFAULT, "INFO",
    )