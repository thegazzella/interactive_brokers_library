# instruments/requests/contract_details.py

from __future__ import annotations

import logging
import threading

from ibapi.contract import Contract, ContractDetails

from .const import _CONTRACT_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class ContractDetailsMixin:
    """
    Mixin that adds contract qualification to TradingApp.

    Overrides:
        contractDetails()             — collects each matching result
        bondContractDetails()         — collects each matching result for bonds
        contractDetailsEnd()          — signals that all results have arrived
        _handle_contract_request_failed() — called by TradingApp.on_request_failed()

    Adds:
        request_contract()            — public method; blocks until resolved or timeout
    """

    def __init__(self) -> None:
        self._contract_details_results: list[ContractDetails] = []
        self._contract_details_event = threading.Event()
        self._contract_details_lock = threading.Lock()
        self._contract_details_req_id: int | None = None
        self._contract_details_failed: bool = False

    # ------------------------------------------------------------------
    # EWrapper callbacks — called by the ibapi reader thread
    # ------------------------------------------------------------------

    def contractDetails(self, reqId: int, contractDetails: ContractDetails) -> None:
        with self._contract_details_lock:
            if reqId == self._contract_details_req_id:
                self._contract_details_results.append(contractDetails)
                logger.debug(
                    "contractDetails received: %s (conId=%s)",
                    contractDetails.contract.localSymbol,
                    contractDetails.contract.conId,
                )

    def bondContractDetails(self, reqId: int, contractDetails: ContractDetails) -> None:
        with self._contract_details_lock:
            if reqId == self._contract_details_req_id:
                self._contract_details_results.append(contractDetails)
                logger.debug(
                    "bondContractDetails received: %s (conId=%s)",
                    contractDetails.contract.localSymbol,
                    contractDetails.contract.conId,
                )

    def contractDetailsEnd(self, reqId: int) -> None:
        with self._contract_details_lock:
            if reqId == self._contract_details_req_id:
                logger.debug("contractDetailsEnd received for reqId=%s", reqId)
                self._contract_details_event.set()

    # ------------------------------------------------------------------
    # Error hook — called by TradingApp.on_request_failed()
    # ------------------------------------------------------------------

    def _handle_contract_request_failed(
        self,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        """
        Called by TradingApp.on_request_failed() for any request-blocking error.
        If reqId matches the in-flight contract request, unblocks
        request_contract() immediately to raise ValueError rather than
        waiting for the full timeout.
        """
        with self._contract_details_lock:
            if reqId == self._contract_details_req_id:
                logger.debug(
                    "_handle_contract_request_failed: unblocking contract request "
                    "reqId=%s errorCode=%s", reqId, errorCode,
                )
                self._contract_details_failed = True
                self._contract_details_event.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_contract(
        self,
        contract:       Contract,
        allow_multiple: bool  = False,
        timeout:        float = _CONTRACT_REQUEST_TIMEOUT,
    ) -> Contract | list[ContractDetails]:
        """
        Resolve an unspecified Contract against IBKR's security definitions.

        Sends reqContractDetails() and blocks until contractDetailsEnd()
        is received or the timeout expires. If IBKR fires a blocking
        error for this request, raises ValueError immediately rather
        than waiting for the full timeout.

        Args:
            contract:       An unresolved Contract built by one of the factories
                            in instruments/contract.py.
            allow_multiple: If True, returns all matching ContractDetails as a
                            list instead of raising on ambiguous results.
                            Useful for option chain queries or bond searches.
            timeout:        Seconds to wait for a response from TWS.

        Returns:
            If allow_multiple=False (default): the single resolved Contract.
            If allow_multiple=True:            list of ContractDetails.

        Raises:
            ValueError:   If IBKR returns zero matching contracts, returns
                          multiple when allow_multiple=False, or fires a
                          blocking error for this request.
            TimeoutError: If TWS does not respond within `timeout` seconds.

        Example:
            contract = make_stock_contract(symbol="AAPL", exchange="SMART", currency="USD")
            resolved = app.request_contract(contract=contract)

            # Option chain query — allow multiple results
            details = app.request_contract(
                contract=make_option_contract(symbol="SPX"),
                allow_multiple=True,
            )
        """
        with self._contract_details_lock:
            self._contract_details_results = []
            self._contract_details_failed = False
            self._contract_details_event.clear()
            req_id = self.nextId()
            self._contract_details_req_id = req_id

        logger.info(
            "Requesting contract details: symbol=%s secType=%s exchange=%s "
            "currency=%s allow_multiple=%s (reqId=%s)",
            contract.symbol,
            contract.secType,
            contract.exchange,
            contract.currency,
            allow_multiple,
            req_id,
        )

        self.reqContractDetails(req_id, contract)

        resolved_in_time = self._contract_details_event.wait(timeout=timeout)

        with self._contract_details_lock:
            results = list(self._contract_details_results)
            failed  = self._contract_details_failed
            self._contract_details_req_id = None

        if not resolved_in_time:
            raise TimeoutError(
                f"request_contract timed out after {timeout}s for "
                f"{contract.symbol} ({contract.secType}). "
                "Check your TWS connection and market data subscriptions."
            )

        if failed or len(results) == 0:
            raise ValueError(
                f"No contract found for {contract.symbol} ({contract.secType}). "
                "Check symbol, exchange, currency and secType."
            )

        if allow_multiple:
            logger.info(
                "request_contract returning %d results for %s (%s)",
                len(results), contract.symbol, contract.secType,
            )
            return results

        if len(results) > 1:
            descriptions = [
                f"{cd.contract.localSymbol} on {cd.contract.exchange} "
                f"(conId={cd.contract.conId})"
                for cd in results
            ]
            raise ValueError(
                f"Ambiguous contract: {len(results)} matches found for "
                f"{contract.symbol} ({contract.secType}). "
                "Narrow your contract definition (e.g. set primaryExchange or exchange):\n"
                + "\n".join(f"  • {d}" for d in descriptions)
            )

        resolved = results[0].contract

        # ------------------------------------------------------------------
        # Sanity checks — when conId is set, IBKR resolves purely by conId
        # and silently ignores all other fields. Log CRITICAL if the resolved
        # contract does not match what was requested so the caller is alerted
        # to a likely conId mistake.
        # ------------------------------------------------------------------
        if contract.symbol and resolved.symbol != contract.symbol:
            logger.critical(
                "Symbol mismatch after resolution: requested=%s resolved=%s — "
                "conId=%s took precedence over symbol. Check your conId.",
                contract.symbol, resolved.symbol, contract.conId,
            )
        if contract.secType and resolved.secType != contract.secType:
            logger.critical(
                "SecType mismatch after resolution: requested=%s resolved=%s — "
                "conId=%s took precedence over secType. Check your conId.",
                contract.secType, resolved.secType, contract.conId,
            )
        if contract.currency and resolved.currency != contract.currency:
            logger.critical(
                "Currency mismatch after resolution: requested=%s resolved=%s — "
                "conId=%s took precedence over currency. Check your conId.",
                contract.currency, resolved.currency, contract.conId,
            )
 
        logger.info(
            "Contract resolved: %s | conId=%s | exchange=%s | currency=%s",
            resolved.localSymbol,
            resolved.conId,
            resolved.exchange,
            resolved.currency,
        )
        return resolved