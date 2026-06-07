# orders/requests/orders.py
#
# OrdersMixin
# -----------
# Mixin that adds order placement, cancellation, and open order queries
# to TradingApp.
#
# Scope
# -----
# Supported:
#   - Place limit orders             (place_limit_order)
#   - Place market orders            (place_market_order)
#   - Cancel orders                  (cancel_order)
#   - Query open orders (this client)(request_open_orders)
#   - Query all open orders          (request_all_open_orders)
#   - Auto-bind TWS orders           (enable_auto_open_orders)
#   - Query completed orders         (request_completed_orders)
#
# Explicitly excluded (future work):
#   - Order modification        — modifyOrder() is not implemented.
#                                 To change an order, cancel and replace.
#   - Waiting for fill          — place_* methods block until TWS
#                                 acknowledges the order (Submitted /
#                                 PreSubmitted) but do NOT wait for
#                                 execution. Monitor orderStatus()
#                                 callbacks in your strategy for fills.
#   - Bracket / complex orders  — use placeOrder() directly on TradingApp
#                                 for OCA groups, bracket orders, etc.
#
# Shared buffer note
# ------------------
# request_open_orders() and request_all_open_orders() share the same
# openOrder / openOrderEnd callbacks and buffer. They must not be called
# concurrently — this is consistent with the library's single-request
# design.
#
# Error routing
# -------------
# TradingApp.on_request_failed() must call:
#   self._handle_order_request_failed(reqId, errorCode, errorString)

from __future__ import annotations

import logging
import threading

from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_cancel import OrderCancel
from ibapi.order_state import OrderState

from ..const import (
    ACKNOWLEDGED_STATUSES,
    OrderStatus,
)

from .const import (
    _PLACE_ORDER_TIMEOUT,
    _REQUEST_OPEN_ORDERS_TIMEOUT,
    _REQUEST_COMPLETED_ORDERS_TIMEOUT,
)

logger = logging.getLogger(__name__)


class OrdersMixin:
    """
    Mixin that adds order management to TradingApp.

    Overrides:
        orderStatus()                   — tracks acknowledgement of placed orders
        openOrder()                     — collects open orders
        openOrderEnd()                  — signals end of open orders response
        completedOrder()                — collects completed orders
        completedOrdersEnd()            — signals end of completed orders response
        _handle_order_request_failed()  — called by TradingApp.on_request_failed()

    Adds:
        place_limit_order()         — place a limit order; blocks until acknowledged
        place_market_order()        — place a market order; blocks until acknowledged
        cancel_order()              — cancel an open order (non-blocking)
        request_open_orders()       — query open orders for this client; blocks
        request_all_open_orders()   — query open orders across all clients; blocks
        enable_auto_open_orders()   — bind TWS manual orders to this client (non-blocking)
        request_completed_orders()  — query completed orders; blocks
    """

    def __init__(self) -> None:
        # --- place order state ---
        self._order_ack_event  = threading.Event()
        self._order_ack_lock   = threading.Lock()
        self._order_ack_req_id: int | None = None
        self._order_ack_status: str | None = None
        self._order_ack_failed: bool = False

        # --- open orders state (shared by request_open_orders and request_all_open_orders) ---
        self._open_orders_results: list[dict] = []
        self._open_orders_event   = threading.Event()
        self._open_orders_lock    = threading.Lock()
        self._open_orders_pending: bool = False

        # --- completed orders state ---
        self._completed_orders_results: list[dict] = []
        self._completed_orders_event    = threading.Event()
        self._completed_orders_lock     = threading.Lock()
        self._completed_orders_pending: bool = False

    # ------------------------------------------------------------------
    # EWrapper callbacks — called by the ibapi reader thread
    # ------------------------------------------------------------------

    def orderStatus(
        self,
        orderId:       int,
        status:        str,
        filled:        float,
        remaining:     float,
        avgFillPrice:  float,
        permId:        int,
        parentId:      int,
        lastFillPrice: float,
        clientId:      int,
        whyHeld:       str,
        mktCapPrice:   float,
    ) -> None:
        logger.info(
            "orderStatus: orderId=%s status=%s filled=%s remaining=%s avgFillPrice=%s",
            orderId, status, filled, remaining, avgFillPrice,
        )
        with self._order_ack_lock:
            if orderId == self._order_ack_req_id:
                self._order_ack_status = status
                if status in {s.value for s in ACKNOWLEDGED_STATUSES}:
                    logger.debug(
                        "Order %s acknowledged with status=%s", orderId, status
                    )
                    self._order_ack_event.set()
                elif status in {OrderStatus.INACTIVE.value, OrderStatus.CANCELLED.value}:
                    logger.warning(
                        "Order %s rejected or inactive: status=%s", orderId, status
                    )
                    self._order_ack_failed = True
                    self._order_ack_event.set()

    def openOrder(
        self,
        orderId:    int,
        contract:   Contract,
        order:      Order,
        orderState: OrderState,
    ) -> None:
        with self._open_orders_lock:
            if self._open_orders_pending:
                self._open_orders_results.append({
                    "order_id": orderId,
                    "contract": contract,
                    "order":    order,
                    "status":   getattr(orderState, "status", ""),
                })
                logger.debug(
                    "openOrder received: orderId=%s symbol=%s action=%s qty=%s",
                    orderId,
                    contract.symbol,
                    order.action,
                    order.totalQuantity,
                )

    def openOrderEnd(self) -> None:
        with self._open_orders_lock:
            if self._open_orders_pending:
                logger.debug(
                    "openOrderEnd received: %d open orders",
                    len(self._open_orders_results),
                )
                self._open_orders_event.set()

    def completedOrder(
        self,
        contract:   Contract,
        order:      Order,
        orderState: OrderState,
    ) -> None:
        with self._completed_orders_lock:
            if self._completed_orders_pending:
                self._completed_orders_results.append({
                    "contract": contract,
                    "order":    order,
                    "status":   getattr(orderState, "status", ""),
                })
                logger.debug(
                    "completedOrder received: symbol=%s action=%s qty=%s status=%s",
                    contract.symbol,
                    order.action,
                    order.totalQuantity,
                    getattr(orderState, "status", ""),
                )

    def completedOrdersEnd(self) -> None:
        with self._completed_orders_lock:
            if self._completed_orders_pending:
                logger.debug(
                    "completedOrdersEnd received: %d completed orders",
                    len(self._completed_orders_results),
                )
                self._completed_orders_event.set()

    def orderBound(self, permId: int, clientId: int, orderId: int) -> None:
        """
        Fired when a manual TWS order is bound to an API client.
        Occurs when clientId=0 calls reqOpenOrders() or when
        enable_auto_open_orders(True) is active.
        Provides the mapping between permId (account-wide unique identifier)
        and the API orderId (specific to this client session).

        permId   : account-wide unique identifier of the bound order
        clientId : the API client ID the order was bound to
        orderId  : the API order ID assigned to the bound order
        """
        logger.info(
            "orderBound: permId=%s clientId=%s orderId=%s",
            permId, clientId, orderId,
        )

    # ------------------------------------------------------------------
    # Error hook — called by TradingApp.on_request_failed()
    # ------------------------------------------------------------------

    def _handle_order_request_failed(
        self,
        reqId:       int,
        errorCode:   int,
        errorString: str,
    ) -> None:
        with self._order_ack_lock:
            if reqId == self._order_ack_req_id:
                logger.debug(
                    "_handle_order_request_failed: unblocking order request "
                    "reqId=%s errorCode=%s", reqId, errorCode,
                )
                self._order_ack_failed = True
                self._order_ack_event.set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request_open_orders_impl(
        self,
        request_fn: callable,
        label:      str,
        timeout:    float,
    ) -> list[dict]:
        """
        Internal: shared implementation for request_open_orders and
        request_all_open_orders. Both use the same openOrder /
        openOrderEnd callbacks and buffer.
        """
        with self._open_orders_lock:
            self._open_orders_results = []
            self._open_orders_event.clear()
            self._open_orders_pending = True

        logger.info("Requesting %s ...", label)
        request_fn()

        completed = self._open_orders_event.wait(timeout=timeout)

        with self._open_orders_lock:
            results = list(self._open_orders_results)
            self._open_orders_pending = False

        if not completed:
            raise TimeoutError(
                f"{label} timed out after {timeout}s. "
                "Check your TWS connection."
            )

        logger.info("%s received: %d orders", label, len(results))
        return results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place_order(
        self,
        contract: Contract,
        order:    Order,
        timeout:  float = _PLACE_ORDER_TIMEOUT,
    ) -> int:
        """
        Place an order and block until TWS acknowledges it.

        Assigns the next available order ID, sends the order to TWS via
        placeOrder(), then blocks until orderStatus fires with Submitted
        or PreSubmitted. Does NOT wait for the order to be filled —
        monitor orderStatus() callbacks in your strategy for fills.

        Order modification is not supported — to change an order,
        cancel it and place a new one.

        The Order object should be built using the factories in
        orders/order.py:
            make_order()        — general factory, all fields optional
            make_limit_order()  — convenience wrapper for LMT orders
            make_market_order() — convenience wrapper for MKT orders

        Args:
            contract: A resolved Contract object.
            order:    An Order object built via make_order() or the
                      convenience factories.
            timeout:  Seconds to wait for acknowledgement from TWS.

        Returns:
            The IBKR order ID assigned to this order.

        Raises:
            ValueError:   If TWS rejects the order.
            TimeoutError: If TWS does not acknowledge within `timeout` seconds.

        Example:
            from orders.order import make_limit_order, make_market_order
            from orders.const import OrderAction

            # Limit order
            order    = make_limit_order(action=OrderAction.BUY, quantity=1, price=5500.0)
            order_id = app.place_order(contract=resolved, order=order)

            # Market order
            order    = make_market_order(action=OrderAction.BUY, quantity=1)
            order_id = app.place_order(contract=resolved, order=order)

            # Any order type via general factory
            from orders.order import make_order
            order = make_order(
                action        = "BUY",
                orderType     = "TRAIL",
                totalQuantity = 1,
                trailStopPrice = 5400.0,
                tif           = "GTC",
            )
            order_id = app.place_order(contract=resolved, order=order)
        """
        with self._order_ack_lock:
            self._order_ack_status = None
            self._order_ack_failed = False
            self._order_ack_event.clear()
            order_id = self.nextId()
            self._order_ack_req_id = order_id

        logger.info(
            "Placing order: orderId=%s action=%s qty=%s type=%s "
            "symbol=%s exchange=%s",
            order_id,
            order.action,
            order.totalQuantity,
            order.orderType,
            contract.symbol,
            contract.exchange,
        )

        self.placeOrder(order_id, contract, order)

        acknowledged = self._order_ack_event.wait(timeout=timeout)

        with self._order_ack_lock:
            failed = self._order_ack_failed
            status = self._order_ack_status
            self._order_ack_req_id = None

        if not acknowledged:
            raise TimeoutError(
                f"Order {order_id} not acknowledged within {timeout}s. "
                "Check your TWS connection."
            )
        if failed:
            raise ValueError(
                f"Order {order_id} rejected by TWS: status={status}. "
                "Check order parameters and account permissions."
            )

        logger.info("Order %s acknowledged: status=%s", order_id, status)
        return order_id

    def cancel_order(
        self,
        order_id:     int,
        order_cancel: OrderCancel | None = None,
    ) -> None:
        """
        Cancel an active order placed by this client session.

        Non-blocking — sends the cancel request to TWS and returns
        immediately. TWS confirms cancellation via orderStatus() with
        status Cancelled. Monitor that callback in your strategy.

        Note: can only cancel orders placed by the same clientId, or
        manually placed TWS orders when using clientId=0.
        Use cancel_all_orders() to cancel across all clients.

        Args:
            order_id:     The IBKR order ID returned by place_limit_order()
                          or place_market_order().
            order_cancel: Optional OrderCancel object to specify
                          manualOrderCancelTime, manualOrderIndicator,
                          or extOperator fields. Pass None for defaults.

        Example:
            app.cancel_order(order_id=order_id)

            # With explicit OrderCancel
            from ibapi.order_cancel import OrderCancel
            oc = OrderCancel()
            oc.manualOrderCancelTime = ""
            app.cancel_order(order_id=order_id, order_cancel=oc)
        """
        logger.info("Cancelling order: orderId=%s", order_id)
        self.cancelOrder(order_id, order_cancel if order_cancel is not None else OrderCancel())

    def cancel_all_orders(
        self,
        order_cancel: OrderCancel | None = None,
    ) -> None:
        """
        Cancel ALL open orders regardless of how or by whom they were placed.

        Non-blocking — sends the global cancel request to TWS and returns
        immediately. TWS confirms each cancellation via orderStatus() with
        status Cancelled for each affected order.

        Note: this cancels orders placed via the API and manually in TWS.
        It affects all client sessions, not just this one.

        Args:
            order_cancel: Optional OrderCancel object to specify
                          manualOrderCancelTime, manualOrderIndicator,
                          or extOperator fields. Pass None for defaults.

        Example:
            app.cancel_all_orders()
        """
        logger.info("Global cancel — cancelling all open orders")
        self.reqGlobalCancel(order_cancel if order_cancel is not None else OrderCancel())

    def request_open_orders(
        self,
        timeout: float = _REQUEST_OPEN_ORDERS_TIMEOUT,
    ) -> list[dict]:
        """
        Request open orders placed by this client session.

        Sends reqOpenOrders() and blocks until openOrderEnd() is received.
        Returns only orders placed by this clientId. Note: clientId=0 also
        receives TWS-owned open orders.

        Args:
            timeout: Seconds to wait for a response from TWS.

        Returns:
            A list of dicts, one per open order, each containing:
                order_id  (int)      : IBKR order ID
                contract  (Contract) : the contract the order is on
                order     (Order)    : full ibapi Order object
                status    (str)      : current order status from OrderState

        Raises:
            TimeoutError: If TWS does not respond within `timeout` seconds.

        Example:
            open_orders = app.request_open_orders()
            for o in open_orders:
                print(o["order_id"], o["contract"].symbol, o["order"].action)
        """
        return self._request_open_orders_impl(
            request_fn = self.reqOpenOrders,
            label      = "request_open_orders",
            timeout    = timeout,
        )

    def request_all_open_orders(
        self,
        timeout: float = _REQUEST_OPEN_ORDERS_TIMEOUT,
    ) -> list[dict]:
        """
        Request all open orders across all clients and TWS.

        Sends reqAllOpenOrders() and blocks until openOrderEnd() is received.
        Returns orders from all client sessions and TWS manual orders.
        Note: no association is made between returned orders and this client.

        Args:
            timeout: Seconds to wait for a response from TWS.

        Returns:
            A list of dicts, one per open order — same structure as
            request_open_orders().

        Raises:
            TimeoutError: If TWS does not respond within `timeout` seconds.

        Example:
            all_orders = app.request_all_open_orders()
            for o in all_orders:
                print(o["order_id"], o["contract"].symbol, o["order"].action)
        """
        return self._request_open_orders_impl(
            request_fn = self.reqAllOpenOrders,
            label      = "request_all_open_orders",
            timeout    = timeout,
        )

    def enable_auto_open_orders(
        self,
        auto_bind: bool,
    ) -> None:
        """
        Request that newly created TWS manual orders be automatically
        associated with this client session.

        Non-blocking — sends the setting to TWS and returns immediately.
        Once enabled, new TWS orders arrive via the openOrder() and
        orderStatus() callbacks.

        Note: this request can only be made from a client with clientId=0.
        Calling it from any other clientId has no effect.

        Args:
            auto_bind: True to bind new TWS orders to this client.
                       False to stop binding.

        Example:
            app.enable_auto_open_orders(auto_bind=True)
        """
        if self.clientId != 0:
            logger.warning(
                "enable_auto_open_orders() has no effect — "
                "only clientId=0 can bind TWS orders. "
                "Current clientId=%s",
                self.clientId,
            )
            return
        logger.info("Setting auto open orders: auto_bind=%s", auto_bind)
        self.reqAutoOpenOrders(auto_bind)

    def request_completed_orders(
        self,
        api_only: bool = False,
        timeout:  float = _REQUEST_COMPLETED_ORDERS_TIMEOUT,
    ) -> list[dict]:
        """
        Request completed (filled or cancelled) orders.

        Sends reqCompletedOrders() and blocks until completedOrdersEnd()
        is received or the timeout expires.

        Args:
            api_only: If True, returns only orders placed via the API.
                      If False, returns all completed orders including
                      those placed manually in TWS.
            timeout:  Seconds to wait for a response from TWS.

        Returns:
            A list of dicts, one per completed order, each containing:
                contract  (Contract)   : the contract that was traded
                order     (Order)      : full ibapi Order object
                status    (str)        : final order status from OrderState

        Raises:
            TimeoutError: If TWS does not respond within `timeout` seconds.

        Example:
            completed = app.request_completed_orders(api_only=True)
            for o in completed:
                print(o["contract"].symbol, o["order"].action,
                      o["order"].totalQuantity, o["status"])
        """
        with self._completed_orders_lock:
            self._completed_orders_results = []
            self._completed_orders_event.clear()
            self._completed_orders_pending = True

        logger.info(
            "Requesting completed orders: api_only=%s ...", api_only
        )
        self.reqCompletedOrders(api_only)

        completed = self._completed_orders_event.wait(timeout=timeout)

        with self._completed_orders_lock:
            results = list(self._completed_orders_results)
            self._completed_orders_pending = False

        if not completed:
            raise TimeoutError(
                f"request_completed_orders timed out after {timeout}s. "
                "Check your TWS connection."
            )

        logger.info(
            "Completed orders received: %d orders", len(results)
        )
        return results