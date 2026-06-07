# market_data/requests/snapshot.py

from __future__ import annotations

import logging
import threading
from decimal import Decimal

from ibapi.common import TickerId
from ibapi.contract import Contract
from ibapi.ticktype import TickTypeEnum

from .const import _SNAPSHOT_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

# Special key for market data type notification — stored alongside tick keys
MARKET_DATA_TYPE_KEY = "market_data_type"

# Build a lookup dict {int -> name} from TickTypeEnum once at import time.
# TickTypeEnum assigns sequential integers to each name starting from 0,
# stored as attributes. We invert that to get fast int -> name lookup.
_TICK_ID_TO_NAME: dict[int, str] = {
    v: k for k, v in vars(TickTypeEnum).items()
    if isinstance(v, int) and not k.startswith("_")
}


def _tick_name(tickType: int) -> str | None:
    """
    Return the name for a raw ibapi tick integer, or None if unknown.
    Used as the storage key in the snapshot dict and for debug logging.
    """
    return _TICK_ID_TO_NAME.get(tickType)


class SnapshotMixin:
    """
    Mixin that adds market data snapshot requests to TradingApp.

    A snapshot is a one-shot request — IBKR returns the current values
    for all requested tick types then fires tickSnapshotEnd to signal
    completion. No streaming subscription is opened.

    The snapshot dict is keyed by tick name strings (e.g. "BID", "ASK")
    derived from TickTypeEnum. Unknown tick IDs are stored under their
    raw integer value.

    Overrides:
        marketDataType()                  — stores live/frozen/delayed notification
        tickPrice()                       — stores float price ticks
        tickSize()                        — stores Decimal size ticks
        tickGeneric()                     — stores float generic ticks
        tickString()                      — stores str string ticks
        tickOptionComputation()           — stores Greeks as plain dict
        tickEFP()                         — stores EFP fields as plain dict
        tickSnapshotEnd()                 — signals completion
        _handle_snapshot_request_failed() — called by TradingApp.on_request_failed()

    Adds:
        request_snapshot()                — public method; blocks until complete or timeout
    """

    def __init__(self) -> None:
        self._snapshot_ticks: dict = {}
        self._snapshot_event = threading.Event()
        self._snapshot_lock = threading.Lock()
        self._snapshot_req_id: int | None = None
        self._snapshot_failed: bool = False

    # ------------------------------------------------------------------
    # EWrapper callbacks — called by the ibapi reader thread
    # ------------------------------------------------------------------

    def marketDataType(self, reqId: TickerId, marketDataType: int) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id:
                self._snapshot_ticks[MARKET_DATA_TYPE_KEY] = marketDataType
                logger.debug(
                    "marketDataType received: reqId=%s type=%s",
                    reqId, marketDataType,
                )

    def tickPrice(
        self,
        reqId:    TickerId,
        tickType: int,
        price:    float,
        attrib:   object,
    ) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id and price > 0:
                key = _tick_name(tickType) or tickType
                self._snapshot_ticks[key] = price
                logger.debug(
                    "tickPrice: reqId=%s tick=%s price=%s", reqId, key, price,
                )

    def tickSize(
        self,
        reqId:    TickerId,
        tickType: int,
        size:     Decimal,
    ) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id:
                key = _tick_name(tickType) or tickType
                self._snapshot_ticks[key] = size
                logger.debug(
                    "tickSize: reqId=%s tick=%s size=%s", reqId, key, size,
                )

    def tickGeneric(
        self,
        reqId:    TickerId,
        tickType: int,
        value:    float,
    ) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id:
                key = _tick_name(tickType) or tickType
                self._snapshot_ticks[key] = value
                logger.debug(
                    "tickGeneric: reqId=%s tick=%s value=%s", reqId, key, value,
                )

    def tickString(
        self,
        reqId:    TickerId,
        tickType: int,
        value:    str,
    ) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id:
                key = _tick_name(tickType) or tickType
                self._snapshot_ticks[key] = value
                logger.debug(
                    "tickString: reqId=%s tick=%s value=%s", reqId, key, value,
                )

    def tickOptionComputation(
        self,
        reqId:      TickerId,
        tickType:   int,
        tickAttrib: int,
        impliedVol: float,
        delta:      float,
        optPrice:   float,
        pvDividend: float,
        gamma:      float,
        vega:       float,
        theta:      float,
        undPrice:   float,
    ) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id:
                key = _tick_name(tickType) or tickType
                self._snapshot_ticks[key] = {
                    "impliedVol": impliedVol,
                    "delta":      delta,
                    "gamma":      gamma,
                    "vega":       vega,
                    "theta":      theta,
                    "optPrice":   optPrice,
                    "pvDividend": pvDividend,
                    "undPrice":   undPrice,
                }
                logger.debug(
                    "tickOptionComputation: reqId=%s tick=%s delta=%s",
                    reqId, key, delta,
                )

    def tickEFP(
        self,
        reqId:                    TickerId,
        tickType:                 int,
        basisPoints:              float,
        formattedBasisPoints:     str,
        totalDividends:           float,
        holdDays:                 int,
        futureLastTradeDate:      str,
        dividendImpact:           float,
        dividendsToLastTradeDate: float,
    ) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id:
                key = _tick_name(tickType) or tickType
                self._snapshot_ticks[key] = {
                    "basisPoints":              basisPoints,
                    "formattedBasisPoints":     formattedBasisPoints,
                    "totalDividends":           totalDividends,
                    "holdDays":                 holdDays,
                    "futureLastTradeDate":      futureLastTradeDate,
                    "dividendImpact":           dividendImpact,
                    "dividendsToLastTradeDate": dividendsToLastTradeDate,
                }
                logger.debug(
                    "tickEFP: reqId=%s tick=%s basisPoints=%s",
                    reqId, key, basisPoints,
                )

    def tickSnapshotEnd(self, reqId: int) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id:
                logger.debug("tickSnapshotEnd received for reqId=%s", reqId)
                self._snapshot_event.set()

    # ------------------------------------------------------------------
    # Error hook — called by TradingApp.on_request_failed()
    # ------------------------------------------------------------------

    def _handle_snapshot_request_failed(
        self,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        with self._snapshot_lock:
            if reqId == self._snapshot_req_id:
                logger.debug(
                    "_handle_snapshot_request_failed: unblocking snapshot request "
                    "reqId=%s errorCode=%s", reqId, errorCode,
                )
                self._snapshot_failed = True
                self._snapshot_event.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_snapshot(
        self,
        contract:      Contract,
        generic_ticks: str   = "",
        is_regulatory: bool = False,
        timeout:       float = _SNAPSHOT_REQUEST_TIMEOUT,
    ) -> dict:
        """
        Request a market data snapshot for a contract.

        Sends reqMktData() with snapshot=True and blocks until
        tickSnapshotEnd() is received or the timeout expires. If IBKR
        fires a blocking error for this request, raises ValueError
        immediately rather than waiting for the full timeout.

        Note: reqMarketDataType() must be called before this method to
        select live, frozen, or delayed data. This is the caller's
        responsibility — typically set once at connection time.

        Args:
            contract:      A resolved Contract object.
            generic_ticks: Comma-separated string of generic tick IDs
                           for additional tick types, e.g. "106,233".
                           Use generic_tick_list() from tick_types.py
                           to build this string. Pass "" for default ticks.
            timeout:       Seconds to wait for a response from TWS.

        Returns:
            A dict keyed by tick name string (from TickTypeEnum) or raw int
            for unknown ticks, plus "market_data_type":
                "BID"               -> float          (tickPrice)
                "BID_SIZE"          -> Decimal         (tickSize)
                "HALTED"            -> float           (tickGeneric)
                "RT_VOLUME"         -> str             (tickString)
                "BID_OPTION_COMPUTATION" -> dict       (tickOptionComputation)
                "BID_EFP_COMPUTATION"    -> dict       (tickEFP)
                "market_data_type"  -> int

        Raises:
            ValueError:   If IBKR fires a blocking error for this request.
            TimeoutError: If TWS does not respond within `timeout` seconds.

        Example:
            from market_data.tick_types import generic_tick_list, GenericTick

            app.reqMarketDataType(MarketDataType.DELAYED)
            ticks = app.request_snapshot(contract=resolved)
            bid  = ticks.get("BID")
            ask  = ticks.get("ASK")
            last = ticks.get("LAST")
        """
        with self._snapshot_lock:
            self._snapshot_ticks = {}
            self._snapshot_failed = False
            self._snapshot_event.clear()
            req_id = self.nextId()
            self._snapshot_req_id = req_id

        logger.info(
            "Requesting snapshot: symbol=%s secType=%s exchange=%s "
            "currency=%s generic_ticks='%s' (reqId=%s)",
            contract.symbol,
            contract.secType,
            contract.exchange,
            contract.currency,
            generic_ticks,
            req_id,
        )

        self.reqMktData(
            req_id,
            contract,
            generic_ticks,
            True,   # snapshot=True
            is_regulatory,  # regulatorySnapshot
            [],     # mktDataOptions
        )

        resolved_in_time = self._snapshot_event.wait(timeout=timeout)

        with self._snapshot_lock:
            ticks  = dict(self._snapshot_ticks)
            failed = self._snapshot_failed
            self._snapshot_req_id = None

        if not resolved_in_time:
            raise TimeoutError(
                f"request_snapshot timed out after {timeout}s for "
                f"{contract.symbol} ({contract.secType}). "
                "Check your TWS connection and market data subscriptions. "
                "Hint: call reqMarketDataType() before request_snapshot()."
            )

        if failed:
            raise ValueError(
                f"request_snapshot failed for {contract.symbol} "
                f"({contract.secType}). "
                "Check market data subscriptions and permissions."
            )

        logger.info(
            "Snapshot received: symbol=%s ticks=%s",
            contract.symbol,
            list(ticks.keys()),
        )
        return ticks