# orders/requests/executions.py
#
# ExecutionsMixin
# ---------------
# Mixin that adds execution history requests to TradingApp via
# reqExecutions(). Fires execDetails() once per matching execution,
# then execDetailsEnd() to signal completion.
# commissionAndFeesReport() is also fired per execution — stored
# alongside the execution it belongs to, keyed by execId.
#
# Callback ordering guarantees (from IBKR documentation)
# -------------------------------------------------------
# - execDetails and commissionAndFeesReport may arrive in any order.
#   commissionAndFeesReport can arrive BEFORE its execDetails — handled
#   via an orphan buffer that is checked on every execDetails arrival.
# - execDetails fires multiple times for combo (BAG) orders — one per
#   leg execution. These are stored as separate entries (5-segment execId).
# - Execution corrections arrive as a new execDetails with the same base
#   execId but a different suffix after the final period. The correction
#   replaces the original entry in place rather than creating a duplicate.
#
# Error routing
# -------------
# TradingApp.on_request_failed() must call:
#   self._handle_executions_request_failed(reqId, errorCode, errorString)

# when market opens we need to check that the segment split forexec id are dots "."

from __future__ import annotations

import logging
import threading

from ibapi.commission_and_fees_report import CommissionAndFeesReport
from ibapi.contract import Contract
from ibapi.execution import Execution, ExecutionFilter

logger = logging.getLogger(__name__)

_REQUEST_EXECUTIONS_TIMEOUT: float = 10.0


def _exec_id_base(exec_id: str) -> str:
    """
    Return the base execId without the correction suffix.

    IBKR execIds are dot-separated segments. A correction to an execution
    has the same base (all segments except the last) but a different final
    segment. By comparing bases we can detect corrections.

    Examples:
        "0001F4460B.0001"         -> "0001F4460B"        (standard, 4-segment)
        "0001F4460B.0001.01"      -> "0001F4460B.0001"   (correction)
        "0001F4460B.0001.L1.0001" -> "0001F4460B.0001.L1" (combo leg, 5-segment)
    """
    return exec_id.rsplit(".", 1)[0]


class ExecutionsMixin:
    """
    Mixin that adds execution history requests to TradingApp.

    Overrides:
        execDetails()                       — collects one result per execution,
                                              handles corrections in place
        execDetailsEnd()                    — signals that all results have arrived
        commissionAndFeesReport()           — attaches commission to matching execution;
                                              buffers orphans that arrive before execDetails
        _handle_executions_request_failed() — called by TradingApp.on_request_failed()

    Adds:
        request_executions() — public method; blocks until complete or timeout
        get_executions()     — returns all executions received so far (including
                               automatic fill notifications)
    """

    def __init__(self) -> None:
        # Results buffer: list of dicts, one per execution (corrections update in place)
        self._executions_results: list[dict] = []

        # Index for fast commission lookup and correction detection:
        #   execId -> dict entry in _executions_results
        self._executions_by_exec_id: dict[str, dict] = {}

        # Index for correction detection:
        #   base execId -> dict entry (the most recent version of each execution)
        self._executions_by_base_id: dict[str, dict] = {}

        # Orphan commissions that arrived before their execDetails:
        #   execId -> CommissionAndFeesReport
        self._orphan_commissions: dict[str, CommissionAndFeesReport] = {}

        self._executions_event = threading.Event()
        self._executions_lock  = threading.Lock()
        self._executions_req_id: int | None = None
        self._executions_failed: bool = False

    # ------------------------------------------------------------------
    # EWrapper callbacks — called by the ibapi reader thread
    # ------------------------------------------------------------------

    def execDetails(
        self,
        reqId:     int,
        contract:  Contract,
        execution: Execution,
    ) -> None:
        """
        Fired per execution in response to reqExecutions(),
        and also automatically when an order is filled.

        Handles three cases:
        1. New execution      — appended to results buffer
        2. Correction         — detected by matching base execId, updates in place
        3. Combo leg fill     — 5-segment execId, treated as a distinct new execution
        """
        exec_id  = execution.execId
        base_id  = _exec_id_base(exec_id)

        with self._executions_lock:
            if base_id in self._executions_by_base_id:
                
                existing = self._executions_by_base_id[base_id]
                old_exec_id = existing["execution"].execId
                logger.debug(
                    "execDetails correction received: base=%s "
                    "old_execId=%s new_execId=%s symbol=%s",
                    base_id, old_exec_id, exec_id, contract.symbol,
                )
                existing["execution"] = execution
                existing["contract"]  = contract
                
                # Re-index under new execId, remove old
                del self._executions_by_exec_id[old_exec_id]
                self._executions_by_exec_id[exec_id] = existing
                self._executions_by_base_id[base_id] = existing
            else:
                
                detail = {
                    "req_id":     reqId,
                    "contract":   contract,
                    "execution":  execution,
                    "commission": None,
                }
                self._executions_results.append(detail)
                self._executions_by_exec_id[exec_id] = detail
                self._executions_by_base_id[base_id] = detail
                logger.debug(
                    "execDetails received: execId=%s symbol=%s side=%s "
                    "shares=%s price=%s time=%s",
                    exec_id,
                    contract.symbol,
                    execution.side,
                    execution.shares,
                    execution.price,
                    execution.time,
                )

            orphan = self._orphan_commissions.pop(exec_id, None)
            if orphan is not None:
                self._executions_by_exec_id[exec_id]["commission"] = orphan
                logger.debug(
                    "Orphan commission attached to execId=%s commission=%s",
                    exec_id, orphan.commission,
                )

    def execDetailsEnd(self, reqId: int) -> None:
        """
        Fired once all executions have been sent in response to
        reqExecutions(). Not fired for automatic fill notifications.
        """
        with self._executions_lock:
            if reqId == self._executions_req_id:
                logger.debug(
                    "execDetailsEnd received for reqId=%s — %d executions",
                    reqId, len(self._executions_results),
                )
                self._executions_event.set()

    def commissionAndFeesReport(
        self,
        commissionAndFeesReport: CommissionAndFeesReport,
    ) -> None:
        """
        Fired per execution immediately after a fill, or in response
        to reqExecutions(). May arrive before or after its execDetails.

        If the matching execution is already in the buffer, attaches
        the commission immediately. Otherwise stores it as an orphan
        to be attached when execDetails arrives.
        """
        exec_id = commissionAndFeesReport.execId
        with self._executions_lock:
            detail = self._executions_by_exec_id.get(exec_id)
            if detail is not None:
                detail["commission"] = commissionAndFeesReport
                logger.debug(
                    "commissionAndFeesReport attached: execId=%s "
                    "commission=%s",
                    exec_id,
                    commissionAndFeesReport,
                )
                
            else:
                self._orphan_commissions[exec_id] = commissionAndFeesReport
                logger.debug(
                    "commissionAndFeesReport buffered as orphan: "
                    "execId=%s — execDetails not yet received",
                    exec_id,
                )

    # ------------------------------------------------------------------
    # Error hook — called by TradingApp.on_request_failed()
    # ------------------------------------------------------------------

    def _handle_executions_request_failed(
        self,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        with self._executions_lock:
            if reqId == self._executions_req_id:
                logger.debug(
                    "_handle_executions_request_failed: unblocking executions "
                    "request reqId=%s errorCode=%s", reqId, errorCode,
                )
                self._executions_failed = True
                self._executions_event.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_executions(
        self,
        execution_filter:  ExecutionFilter | None = None,
        timeout: float = _REQUEST_EXECUTIONS_TIMEOUT,
    ) -> list[dict]:
        """
        Request execution history for the current session.

        Sends reqExecutions() and blocks until execDetailsEnd() is
        received or the timeout expires.

        ExecId behaviour (from IBKR documentation):
        - Standard orders: 4-segment execId e.g. "0001F4460B.0001"
        - Combo/BAG orders: 5-segment execId per leg e.g. "0001F4460B.0001.L1.0001"
        - Corrections: new execDetails with same base but different final segment —
          the original entry is updated in place, not duplicated
        - commissionAndFeesReport may arrive before or after its execDetails —
          handled transparently via an orphan buffer

        Args:
            filter:  Optional ExecutionFilter to narrow results by clientId,
                     acctCode, time, symbol, secType, exchange, or side.
                     Pass None to retrieve all executions since midnight.
            timeout: Seconds to wait for a response from TWS.

        Returns:
            A list of dicts, one per execution, each containing:
                req_id     (int)                         : request ID
                contract   (Contract)                    : traded contract
                execution  (Execution)                   : fill details including
                                                           execId, time, side,
                                                           shares, price, orderId
                commission (CommissionAndFeesReport|None): commission data,
                                                           or None if not yet received

        Raises:
            ValueError:   If IBKR fires a blocking error for this request.
            TimeoutError: If TWS does not respond within `timeout` seconds.

        Example:
            executions = app.request_executions()
            for e in executions:
                print(e["execution"].execId, e["contract"].symbol,
                      e["execution"].side, e["execution"].shares,
                      e["execution"].price)

            # Filtered by symbol
            from ibapi.execution import ExecutionFilter
            f = ExecutionFilter()
            f.symbol = "SPX"
            executions = app.request_executions(filter=f)
        """
        exec_filter = execution_filter if execution_filter is not None else ExecutionFilter()

        with self._executions_lock:
            self._executions_results      = []
            self._executions_by_exec_id   = {}
            self._executions_by_base_id   = {}
            self._orphan_commissions      = {}
            self._executions_failed       = False
            self._executions_event.clear()
            req_id = self.nextId()
            self._executions_req_id = req_id

        logger.info("Requesting executions (reqId=%s) ...", req_id)
        self.reqExecutions(req_id, exec_filter)

        resolved_in_time = self._executions_event.wait(timeout=timeout)

        with self._executions_lock:
            results = list(self._executions_results)
            failed  = self._executions_failed
            self._executions_req_id = None

        if not resolved_in_time:
            raise TimeoutError(
                f"request_executions timed out after {timeout}s. "
                "Check your TWS connection."
            )

        if failed:
            raise ValueError(
                "request_executions failed. "
                "Check your TWS connection and permissions."
            )

        logger.info("Executions received: %d results", len(results))
        return results

    def get_executions(self) -> list[dict]:
        """
        Return all executions received so far in this session,
        including automatic fill notifications fired outside of a
        reqExecutions() request.

        Non-blocking — returns whatever is currently in the buffer.
        Corrections are already applied in place so the list always
        reflects the most recent version of each execution.

        Returns:
            A list of dicts (may be empty), same structure as
            request_executions().
        """
        with self._executions_lock:
            return list(self._executions_results)
