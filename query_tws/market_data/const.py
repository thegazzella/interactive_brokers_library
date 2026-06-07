# market_data/const.py
#
# Shared constants for all market data mixins.

from __future__ import annotations

from enum import IntEnum

# Default timeout in seconds for snapshot requests
_SNAPSHOT_REQUEST_TIMEOUT: float = 10.0


class MarketDataType(IntEnum):
    """
    Market data type passed to reqMarketDataType().
    Must be called before reqMktData to select live, frozen, or delayed data.
    Call once at connection time — applies to all subsequent subscriptions.

    Reference: https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/#market-data-type
    """
    LIVE           = 1   # live data — requires market data subscription
    FROZEN         = 2   # last available price if market is closed
    DELAYED        = 3   # delayed data — no subscription required
    DELAYED_FROZEN = 4   # delayed frozen — delayed + last available if closed