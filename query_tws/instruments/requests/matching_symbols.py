# instruments/requests/matching_symbols.py

from __future__ import annotations

import logging
import threading

from ibapi.contract import ContractDescription

from .const import _MATCHING_SYMBOLS_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class MatchingSymbolsMixin:
    """
    Mixin that adds symbol search to TradingApp.

    Overrides:
        symbolSamples()                          — captures the single callback
        _handle_matching_symbols_request_failed() — called by TradingApp.on_request_failed()

    Adds:
        request_matching_symbols() — public method; blocks until complete or timeout

    Note: IBKR enforces a minimum interval of 1 second between successive
    calls to reqMatchingSymbols. The caller is responsible for respecting
    this constraint.
    """

    def __init__(self) -> None:
        self._matching_symbols_results: list[ContractDescription] = []
        self._matching_symbols_event = threading.Event()
        self._matching_symbols_lock = threading.Lock()
        self._matching_symbols_req_id: int | None = None
        self._matching_symbols_failed: bool = False

    # ------------------------------------------------------------------
    # EWrapper callback — called once by the ibapi reader thread
    # ------------------------------------------------------------------

    def symbolSamples(
        self,
        reqId:                int,
        contractDescriptions: list[ContractDescription],
    ) -> None:
        with self._matching_symbols_lock:
            if reqId == self._matching_symbols_req_id:
                self._matching_symbols_results = list(contractDescriptions)
                logger.debug(
                    "symbolSamples received: %d results (reqId=%s)",
                    len(contractDescriptions),
                    reqId,
                )
                self._matching_symbols_event.set()

    # ------------------------------------------------------------------
    # Error hook — called by TradingApp.on_request_failed()
    # ------------------------------------------------------------------

    def _handle_matching_symbols_request_failed(
        self,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        """
        Called by TradingApp.on_request_failed() for any request-blocking error.
        If reqId matches the in-flight symbol search request, unblocks
        request_matching_symbols() immediately to raise ValueError rather
        than waiting for the full timeout.
        """
        with self._matching_symbols_lock:
            if reqId == self._matching_symbols_req_id:
                logger.debug(
                    "_handle_matching_symbols_request_failed: unblocking "
                    "matching symbols request reqId=%s errorCode=%s",
                    reqId, errorCode,
                )
                self._matching_symbols_failed = True
                self._matching_symbols_event.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_matching_symbols(
        self,
        pattern: str,
        timeout: float = _MATCHING_SYMBOLS_REQUEST_TIMEOUT,
    ) -> list[ContractDescription]:
        """
        Search for stock contracts matching a symbol or company name pattern.

        Sends reqMatchingSymbols() and blocks until symbolSamples() is
        received or the timeout expires. If IBKR fires a blocking error
        for this request, raises ValueError immediately rather than
        waiting for the full timeout.

        Note: IBKR enforces a minimum interval of 1 second between successive
        calls to reqMatchingSymbols. The caller is responsible for respecting
        this constraint.

        Args:
            pattern: Start of a ticker symbol (e.g. "IB", "AAPL") or a word
                     from the company name (e.g. "Interactive"). Case-insensitive.
            timeout: Seconds to wait for a response from TWS.

        Returns:
            A list of ContractDescription objects, each containing:
                contract            (Contract) : partially populated contract with
                                                 conId, symbol, secType,
                                                 primaryExchange, currency,
                                                 description, issuerId
                derivativeSecTypes  (list[str]): derivative types available on the
                                                 underlying e.g. ["OPT", "WAR", "FUT"]

        Raises:
            ValueError:   If no matching symbols are found or IBKR fires a
                          blocking error for this request.
            TimeoutError: If TWS does not respond within `timeout` seconds.

        Example:
            results = app.request_matching_symbols(pattern="Interactive")
            for cd in results:
                print(cd.contract.symbol, cd.contract.primaryExchange)
        """
        with self._matching_symbols_lock:
            self._matching_symbols_results = []
            self._matching_symbols_failed = False
            self._matching_symbols_event.clear()
            req_id = self.nextId()
            self._matching_symbols_req_id = req_id

        logger.info(
            "Requesting matching symbols: pattern='%s' (reqId=%s)",
            pattern,
            req_id,
        )

        self.reqMatchingSymbols(req_id, pattern)

        resolved_in_time = self._matching_symbols_event.wait(timeout=timeout)

        with self._matching_symbols_lock:
            results = list(self._matching_symbols_results)
            failed  = self._matching_symbols_failed
            self._matching_symbols_req_id = None

        if not resolved_in_time:
            raise TimeoutError(
                f"request_matching_symbols timed out after {timeout}s "
                f"for pattern='{pattern}'. "
                "Check your TWS connection."
            )

        if failed:
            raise ValueError(
                f"request_matching_symbols failed for pattern='{pattern}'. "
                "Check your TWS connection and permissions."
            )

        if len(results) == 0:
            raise ValueError(
                f"No matching symbols found for pattern='{pattern}'."
            )

        logger.info(
            "Matching symbols received: pattern='%s' results=%s",
            pattern,
            [cd.contract.symbol for cd in results],
        )
        return results