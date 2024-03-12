"""Constants for the Logger integration."""

import logging

DOMAIN = "logger"

SERVICE_SET_DEFAULT_LEVEL = "set_default_level"
SERVICE_SET_LEVEL = "set_level"

LOGSEVERITY_NOTSET = "NOTSET"
LOGSEVERITY_DEBUG = "DEBUG"
LOGSEVERITY_INFO = "INFO"
LOGSEVERITY_WARNING = "WARNING"
LOGSEVERITY_ERROR = "ERROR"
LOGSEVERITY_CRITICAL = "CRITICAL"
LOGSEVERITY_WARN = "WARN"
LOGSEVERITY_FATAL = "FATAL"

LOGSEVERITY = {
    LOGSEVERITY_CRITICAL: logging.CRITICAL,
    LOGSEVERITY_FATAL: logging.FATAL,
    LOGSEVERITY_ERROR: logging.ERROR,
    LOGSEVERITY_WARNING: logging.WARNING,
    LOGSEVERITY_WARN: logging.WARN,
    LOGSEVERITY_INFO: logging.INFO,
    LOGSEVERITY_DEBUG: logging.DEBUG,
    LOGSEVERITY_NOTSET: logging.NOTSET,
}


DEFAULT_LOGSEVERITY = "DEBUG"

LOGGER_DEFAULT = "default"
LOGGER_LOGS = "logs"
LOGGER_FILTERS = "filters"

ATTR_LEVEL = "level"

STORAGE_KEY = "core.logger"
STORAGE_LOG_KEY = "logs"
STORAGE_VERSION = 1
