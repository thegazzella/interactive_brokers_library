# trading_app.py

from __future__ import annotations

import logging

from ibapi.client import EClient
from ibapi.common import OrderId
from ibapi.wrapper import EWrapper

from .errors import ErrorDispatcherMixin
from .instruments import ContractDetailsMixin, MatchingSymbolsMixin, OptParamsMixin
from .market_data import SnapshotMixin
from .orders import ExecutionsMixin, OrdersMixin

logger = logging.getLogger(__name__)


class TradingApp(
    EClient,
    ContractDetailsMixin,
    OptParamsMixin,
    MatchingSymbolsMixin,
    SnapshotMixin,
    OrdersMixin,
    ExecutionsMixin,
    ErrorDispatcherMixin,
    EWrapper,
):

    def __init__(self) -> None:
        EClient.__init__(self, wrapper=self)
        ContractDetailsMixin.__init__(self)
        OptParamsMixin.__init__(self)
        MatchingSymbolsMixin.__init__(self)
        SnapshotMixin.__init__(self)
        OrdersMixin.__init__(self)
        ExecutionsMixin.__init__(self)
        self.orderId: OrderId | None = None
        self.received_time: int | None = None

    def currentTime(self, time: int) -> None:
        self.received_time = time
        logger.info("Current time: %s", self.received_time)

    # ------------------------------------------------------------------
    # Connection callbacks
    # ------------------------------------------------------------------

    def connectAck(self) -> None:
        logger.info("Connection acknowledged by TWS.")

    # ------------------------------------------------------------------
    # Order IDs
    # ------------------------------------------------------------------

    def nextValidId(self, orderId: OrderId) -> None:
        self.orderId = orderId

    def nextId(self) -> OrderId:
        self.orderId += 1
        return self.orderId

    # ------------------------------------------------------------------
    # Errors — classification delegated to ErrorDispatcherMixin
    # ------------------------------------------------------------------

    def winError(self, text: str, lastError: int) -> None:
        logger.critical(
            "WinError %s: %s — socket connection lost, reconnect required.",
            lastError, text,
        )

    def error(
        self,
        reqId:                   int,
        errorTime:               int,
        errorCode:               int,
        errorString:             str,
        advancedOrderRejectJson: str = "",
    ) -> None:
        self.dispatch_error(
            reqId       = reqId,
            errorCode   = errorCode,
            errorString = errorString,
        )

    # ------------------------------------------------------------------
    # Request failure routing — single definition, explicit delegation
    # ------------------------------------------------------------------

    def on_request_failed(
        self,
        *,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        """
        Called by ErrorDispatcherMixin for any request-blocking error.
        Explicitly delegates to each mixin that owns in-flight requests.
        Each mixin checks its own reqId and reacts only if it matches.
        """
        self._handle_contract_request_failed(reqId, errorCode, errorString)
        self._handle_opt_params_request_failed(reqId, errorCode, errorString)
        self._handle_matching_symbols_request_failed(reqId, errorCode, errorString)
        self._handle_snapshot_request_failed(reqId, errorCode, errorString)
        self._handle_order_request_failed(reqId, errorCode, errorString)
        self._handle_executions_request_failed(reqId, errorCode, errorString)

    # ------------------------------------------------------------------
    # Connection loss routing
    # ------------------------------------------------------------------

    def on_connection_lost(
        self,
        *,
        errorCode:   int,
        errorString: str,
    ) -> None:
        logger.critical(
            "Connection lost [%d]: %s", errorCode, errorString,
        )