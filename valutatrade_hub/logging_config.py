import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from .constants import (
    LOG_BACKUP_COUNT_DEFAULT,
    LOG_FILE_DEFAULT,
    LOG_FILE_SIZE_DEFAULT,
    LOG_ROTATION_DEFAULT,
)
from .infra.settings import BASE_DIR, SettingsLoader

_LOGGER_NAME = "valutatrade"
_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_DEFAULT_LEVEL = "INFO"

_configured = False


def setup_logging():
    """Настроить логгер "valutatrade".
    Повторный вызов ничего не делает
    """
    
    global _configured
    if _configured:
        return

    settings = SettingsLoader()

    level_name = settings.get("log_level", _DEFAULT_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)

    log_format = settings.get("log_format", _DEFAULT_FORMAT)
    log_file = BASE_DIR / settings.get("log_file", LOG_FILE_DEFAULT)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    rotation = settings.get("log_rotation", LOG_ROTATION_DEFAULT)
    backup_count = settings.get("log_backup_count", LOG_BACKUP_COUNT_DEFAULT)

    if rotation == "size":
        file_size = settings.get("log_file_size", LOG_FILE_SIZE_DEFAULT)
        handler = RotatingFileHandler(
            log_file,
            maxBytes=file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:
        handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=backup_count,
            encoding="utf-8",
        )

    handler.setFormatter(logging.Formatter(log_format))

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(handler)

    _configured = True