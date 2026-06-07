# instruments/requests/opt_params.py

from __future__ import annotations

import logging
import threading

from ibapi.common import SetOfFloat, SetOfString

from .const import _OPT_PARAMS_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class OptParamsMixin:
    """
    Mixin that adds option chain parameter requests to TradingApp.

    Overrides:
        securityDefinitionOptionParameter()       — collects one result per exchange
        securityDefinitionOptionParameterEnd()    — signals that all results have arrived
        _handle_opt_params_request_failed()       — called by TradingApp.on_request_failed()

    Adds:
        request_opt_params() — public method; blocks until complete or timeout
    """

    def __init__(self) -> None:
        self._opt_params_results: list[dict] = []
        self._opt_params_event = threading.Event()
        self._opt_params_lock = threading.Lock()
        self._opt_params_req_id: int | None = None
        self._opt_params_failed: bool = False

    # ------------------------------------------------------------------
    # EWrapper callbacks — called by the ibapi reader thread
    # ------------------------------------------------------------------

    def securityDefinitionOptionParameter(
        self,
        reqId:           int,
        exchange:        str,
        underlyingConId: int,
        tradingClass:    str,
        multiplier:      str,
        expirations:     SetOfString,
        strikes:         SetOfFloat,
    ) -> None:
        with self._opt_params_lock:
            if reqId == self._opt_params_req_id:
                self._opt_params_results.append({
                    "exchange":        exchange,
                    "underlyingConId": underlyingConId,
                    "tradingClass":    tradingClass,
                    "multiplier":      multiplier,
                    "expirations":     expirations,
                    "strikes":         strikes,
                })
                logger.debug(
                    "securityDefinitionOptionParameter received: exchange=%s "
                    "tradingClass=%s multiplier=%s expirations=%d strikes=%d",
                    exchange, tradingClass, multiplier,
                    len(expirations), len(strikes),
                )

    def securityDefinitionOptionParameterEnd(self, reqId: int) -> None:
        with self._opt_params_lock:
            if reqId == self._opt_params_req_id:
                logger.debug(
                    "securityDefinitionOptionParameterEnd received for reqId=%s", reqId
                )
                self._opt_params_event.set()

    # ------------------------------------------------------------------
    # Error hook — called by TradingApp.on_request_failed()
    # ------------------------------------------------------------------

    def _handle_opt_params_request_failed(
        self,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        """
        Called by TradingApp.on_request_failed() for any request-blocking error.
        If reqId matches the in-flight opt params request, unblocks
        request_opt_params() immediately to raise ValueError rather than
        waiting for the full timeout.
        """
        with self._opt_params_lock:
            if reqId == self._opt_params_req_id:
                logger.debug(
                    "_handle_opt_params_request_failed: unblocking opt params request "
                    "reqId=%s errorCode=%s", reqId, errorCode,
                )
                self._opt_params_failed = True
                self._opt_params_event.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_opt_params(
        self,
        underlying_symbol:   str,
        fut_fop_exchange:    str,
        underlying_sec_type: str,
        underlying_con_id:   int,
        timeout:             float = _OPT_PARAMS_REQUEST_TIMEOUT,
    ) -> list[dict]:
        """
        Request option chain parameters for an underlying instrument.

        Sends reqSecDefOptParams() and blocks until
        securityDefinitionOptionParameterEnd() is received or the timeout
        expires. If IBKR fires a blocking error for this request, raises
        ValueError immediately rather than waiting for the full timeout.

        Args:
            underlying_symbol:   Root symbol of the underlying, e.g. "SPX", "AAPL".
            fut_fop_exchange:    Exchange for futures/FOPs. Pass "" for all exchanges
                                 or for equity options (e.g. "CME" for ES options).
            underlying_sec_type: secType of the underlying, e.g. "STK", "IND", "FUT".
            underlying_con_id:   conId of the resolved underlying contract.
            timeout:             Seconds to wait for a response from TWS.

        Returns:
            A list of dicts, one per exchange, each containing:
                exchange        (str)         : exchange name
                underlyingConId (int)         : conId of the underlying
                tradingClass    (str)         : option trading class e.g. "SPXW"
                multiplier      (str)         : contract multiplier e.g. "100"
                expirations     (SetOfString) : available expiry dates (YYYYMMDD)
                strikes         (SetOfFloat)  : available strike prices

        Raises:
            ValueError:   If no option parameters are returned or IBKR fires
                          a blocking error for this request.
            TimeoutError: If TWS does not respond within `timeout` seconds.

        Example:
            params = app.request_opt_params(
                underlying_symbol   = "SPX",
                fut_fop_exchange    = "",
                underlying_sec_type = "IND",
                underlying_con_id   = resolved.conId,
            )
        """
        with self._opt_params_lock:
            self._opt_params_results = []
            self._opt_params_failed = False
            self._opt_params_event.clear()
            req_id = self.nextId()
            self._opt_params_req_id = req_id

        logger.info(
            "Requesting option params: symbol=%s secType=%s conId=%s "
            "exchange='%s' (reqId=%s)",
            underlying_symbol,
            underlying_sec_type,
            underlying_con_id,
            fut_fop_exchange,
            req_id,
        )

        self.reqSecDefOptParams(
            req_id,
            underlying_symbol,
            fut_fop_exchange,
            underlying_sec_type,
            underlying_con_id,
        )

        resolved_in_time = self._opt_params_event.wait(timeout=timeout)

        with self._opt_params_lock:
            results = list(self._opt_params_results)
            failed  = self._opt_params_failed
            self._opt_params_req_id = None

        if not resolved_in_time:
            raise TimeoutError(
                f"request_opt_params timed out after {timeout}s for "
                f"{underlying_symbol} ({underlying_sec_type}). "
                "Check your TWS connection and market data subscriptions."
            )

        if failed:
            raise ValueError(
                f"request_opt_params failed for {underlying_symbol} "
                f"({underlying_sec_type}, conId={underlying_con_id}). "
                "Check symbol, exchange and market data subscriptions."
            )

        if len(results) == 0:
            raise ValueError(
                f"No option parameters found for {underlying_symbol} "
                f"({underlying_sec_type}, conId={underlying_con_id}). "
                "Check that the underlying has listed options."
            )

        logger.info(
            "Option params received: symbol=%s exchanges=%s total_results=%d",
            underlying_symbol,
            [r["exchange"] for r in results],
            len(results),
        )
        return results