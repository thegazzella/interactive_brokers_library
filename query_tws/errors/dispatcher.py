# errors/dispatcher.py
#
# ErrorDispatcherMixin
# --------------------
# Centralises all IBKR error code routing. Add to TradingApp and call
# dispatch_error() once from error(). The dispatcher classifies the code,
# logs at the appropriate level, and calls named hooks.
#
# No other file in the library should reference raw error codes or
# import from error_severity.py directlsy — everything flows through here.
#
# Adding a new hook
# -----------------
# 1. Add/classify the code in error_severity.py if not already there
# 2. Add a default no-op hook below
# 3. Override that hook in the relevant mixin

from __future__ import annotations

import logging

from .error_codes import ERROR_CODES
from .error_severity import (
    ErrorSeverity,
    REQUEST_BLOCKING_CODES,
    classify,
)

logger = logging.getLogger(__name__)


class ErrorDispatcherMixin:
    """
    Mixin that classifies IBKR error codes and routes them to named hooks.

    Adds:
        dispatch_error()     — call this from TradingApp.error()

    Named hooks (override in the relevant mixin, no-ops by default):
        on_request_failed()  — called for any REQUEST_BLOCKING_CODES
        on_connection_lost() — called for CRITICAL connectivity codes
    """

    def dispatch_error(
        self,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        """
        Classify an IBKR error code, log at the appropriate level,
        and call the relevant named hook.

        INFO codes are silently debug-logged and ignored.
        WARNING codes are logged as warnings — no hook called.
        ERROR codes call on_request_failed().
        CRITICAL codes call on_request_failed() and on_connection_lost().

        Args:
            reqId:       Request ID from TradingApp.error().
            errorCode:   Numeric error code from TradingApp.error().
            errorString: Human-readable error string from TradingApp.error().
        """
        severity = classify(errorCode)

        # Enrich the message from the registry if available
        registry_entry = ERROR_CODES.get(errorCode)
        message = registry_entry[0] if registry_entry else errorString

        if severity == ErrorSeverity.INFO:
            logger.debug("[%d] %s", errorCode, message)
            return

        if severity == ErrorSeverity.WARNING:
            logger.warning("[%d] reqId=%s — %s", errorCode, reqId, message)
            return

        if severity == ErrorSeverity.ERROR:
            logger.error("[%d] reqId=%s — %s", errorCode, reqId, message)
            if errorCode in REQUEST_BLOCKING_CODES:
                self.on_request_failed(
                    reqId       = reqId,
                    errorCode   = errorCode,
                    errorString = errorString,
                )
            return

        if severity == ErrorSeverity.CRITICAL:
            logger.critical("[%d] reqId=%s — %s", errorCode, reqId, message)
            self.on_request_failed(
                reqId       = reqId,
                errorCode   = errorCode,
                errorString = errorString,
            )
            self.on_connection_lost(
                errorCode   = errorCode,
                errorString = errorString,
            )
            return

    # ------------------------------------------------------------------
    # Default hook implementations — no-ops, override in mixins
    # ------------------------------------------------------------------

    def on_request_failed(
        self,
        *,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        """
        Called for any error code in REQUEST_BLOCKING_CODES or CRITICAL.
        Override in any mixin that has in-flight requests to unblock.

        Each mixin compares reqId against its own in-flight reqId and
        reacts only if they match — no knowledge of error codes needed.

        Args:
            reqId:       The request ID that triggered the error.
            errorCode:   The IBKR error code (for logging/context only).
            errorString: The IBKR error string (for logging/context only).
        """
        pass

    def on_connection_lost(
        self,
        *,
        errorCode:   int,
        errorString: str,
    ) -> None:
        """
        Called for CRITICAL connection-level errors (lost connectivity,
        port reset, etc.). Override to implement reconnect logic.

        Args:
            errorCode:   The IBKR error code.
            errorString: The IBKR error string.
        """
        pass