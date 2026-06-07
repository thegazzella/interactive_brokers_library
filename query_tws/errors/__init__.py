# errors/__init__.py

from .dispatcher import ErrorDispatcherMixin
from .error_codes import ERROR_CODES
from .error_severity import (
    ERROR_CODES_SET,
    CONNECTION_CODES,
    INFO_ONLY_CODES,
    REQUEST_BLOCKING_CODES,
    WARNING_ONLY_CODES,
    ErrorSeverity,
    classify,
)

__all__ = [
    "ErrorDispatcherMixin",
    "ErrorSeverity",
    "ERROR_CODES",
    "INFO_ONLY_CODES",
    "WARNING_ONLY_CODES",
    "ERROR_CODES_SET",
    "CONNECTION_CODES",
    "REQUEST_BLOCKING_CODES",
    "classify",
]