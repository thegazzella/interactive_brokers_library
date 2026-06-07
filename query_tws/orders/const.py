# orders/const.py
#
# Shared constants and enums for the orders module.

from __future__ import annotations

from enum import Enum


class OrderAction(str, Enum):
    """
    Order side. Use BUY to open a long or close a short.
    Use SELL to close a long or open a short position.
    IBKR infers whether a SELL is a closing or short-opening trade
    from the account's current position — no separate short-sell
    request is needed for standard retail accounts.
    For institutional accounts or self-locate shorts, pass
    short_sale_slot and designated_location explicitly.
    """
    BUY  = "BUY"
    SELL = "SELL"


class TimeInForce(str, Enum):
    """
    Time in force for an order.
    Only DAY is currently used as default — all values are defined
    here for future use.
    """
    DAY = "DAY"   # expires at end of trading day — default
    GTC = "GTC"   # good till cancelled
    IOC = "IOC"   # immediate or cancel — fill what's available, cancel rest
    FOK = "FOK"   # fill or kill — fill entirely or cancel immediately
    OPG = "OPG"   # at the opening
    MOC = "MOC"   # market on close
    GTD = "GTD"   # good till date


class OrderStatus(str, Enum):
    """
    Subset of IBKR order status strings relevant to acknowledgement.
    Used to determine when a placed order has been accepted by TWS.
    """
    PRE_SUBMITTED = "PreSubmitted"   # received by TWS, not yet sent to exchange
    SUBMITTED     = "Submitted"      # sent to exchange and acknowledged
    FILLED        = "Filled"         # fully filled
    CANCELLED     = "Cancelled"      # cancelled
    INACTIVE      = "Inactive"       # rejected or inactive


# Statuses that mean TWS has acknowledged the order
ACKNOWLEDGED_STATUSES = frozenset({
    OrderStatus.PRE_SUBMITTED,
    OrderStatus.SUBMITTED,
})