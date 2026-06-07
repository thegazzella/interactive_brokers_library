# tests/test_snapshot.py
#
# Tests for market data snapshot requests across all four MarketDataTypes.
#
# Run all:
#   python -m pytest tests/test_snapshot.py -v
#
# Unit tests only (no TWS):
#   python -m pytest tests/test_snapshot.py -v -m "not integration"
#
# Integration tests (TWS required):
#   python -m pytest tests/test_snapshot.py -v -m integration

from __future__ import annotations

import threading
import time
import unittest

import pytest

from query_tws.instruments.contract import make_contract
from query_tws.market_data import MarketDataType
from query_tws.market_data.requests.snapshot import (
    MARKET_DATA_TYPE_KEY,
    _TICK_ID_TO_NAME,
)
from query_tws.trading_app import TradingApp

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

TWS_HOST  = "127.0.0.1"
TWS_PORT  = 7497
CLIENT_ID = 11

SPX_CON_ID = 416904

CORE_TICKS = {"CLOSE", "BID", "ASK", "LAST"}


def connect_app() -> TradingApp:
    app = TradingApp()
    app.connect(TWS_HOST, TWS_PORT, CLIENT_ID)
    threading.Thread(target=app.run, daemon=True).start()
    deadline = time.time() + 10
    while app.orderId is None:
        if time.time() > deadline:
            raise ConnectionError(
                "TWS did not respond within 10s — is it running with API enabled?"
            )
        time.sleep(0.1)
    return app


def disconnect_app(app: TradingApp) -> None:
    time.sleep(0.5)
    app.disconnect()


def make_spx():
    return make_contract(
        conId    = SPX_CON_ID,
        symbol   = "SPX",
        exchange = "CBOE",
        currency = "USD",
        secType  = "IND",
    )


# ---------------------------------------------------------------------------
# Unit tests — no TWS required
# ---------------------------------------------------------------------------

class TestTickIdToName(unittest.TestCase):
    """Tests for the _TICK_ID_TO_NAME lookup dict built from TickTypeEnum."""

    def test_bid_is_1(self):
        self.assertEqual(_TICK_ID_TO_NAME.get(1), "BID")

    def test_ask_is_2(self):
        self.assertEqual(_TICK_ID_TO_NAME.get(2), "ASK")

    def test_last_is_4(self):
        self.assertEqual(_TICK_ID_TO_NAME.get(4), "LAST")

    def test_close_is_9(self):
        self.assertEqual(_TICK_ID_TO_NAME.get(9), "CLOSE")

    def test_unknown_returns_none(self):
        self.assertIsNone(_TICK_ID_TO_NAME.get(9999))

    def test_non_empty(self):
        self.assertGreater(len(_TICK_ID_TO_NAME), 0)


# ---------------------------------------------------------------------------
# Integration tests — one class per MarketDataType
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestSnapshotFrozen(unittest.TestCase):
    """
    Snapshot using FROZEN market data.
    Safe to run any day — returns last available price even when
    the market is closed.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = connect_app()
        cls.app.reqMarketDataType(MarketDataType.FROZEN)
        cls.ticks = cls.app.request_snapshot(contract=make_spx())

    @classmethod
    def tearDownClass(cls):
        disconnect_app(cls.app)

    def test_returns_non_empty_dict(self):
        self.assertIsInstance(self.ticks, dict)
        self.assertGreater(len(self.ticks), 0)

    def test_market_data_type_key_present(self):
        self.assertIn(MARKET_DATA_TYPE_KEY, self.ticks)

    def test_market_data_type_is_frozen(self):
        self.assertEqual(self.ticks[MARKET_DATA_TYPE_KEY], MarketDataType.FROZEN)

    def test_close_price_present(self):
        self.assertIn("CLOSE", self.ticks)

    def test_close_price_is_positive(self):
        self.assertGreater(self.ticks["CLOSE"], 0)

    def test_all_keys_are_strings_or_ints(self):
        for key in self.ticks:
            self.assertIsInstance(key, (str, int))


@pytest.mark.integration
class TestSnapshotDelayed(unittest.TestCase):
    """
    Snapshot using DELAYED market data.
    No subscription required. Returns 15-min delayed prices.
    Only meaningful during market hours (Mon-Fri 9:30-16:00 ET).
    """

    @classmethod
    def setUpClass(cls):
        cls.app = connect_app()
        cls.app.reqMarketDataType(MarketDataType.DELAYED)
        cls.ticks = cls.app.request_snapshot(contract=make_spx())

    @classmethod
    def tearDownClass(cls):
        disconnect_app(cls.app)

    def test_returns_non_empty_dict(self):
        self.assertIsInstance(self.ticks, dict)
        self.assertGreater(len(self.ticks), 0)

    def test_market_data_type_key_present(self):
        self.assertIn(MARKET_DATA_TYPE_KEY, self.ticks)

    def test_market_data_type_is_delayed(self):
        self.assertEqual(self.ticks[MARKET_DATA_TYPE_KEY], MarketDataType.DELAYED)

    def test_delayed_close_present(self):
        self.assertIn("DELAYED_CLOSE", self.ticks)

    def test_delayed_close_is_positive(self):
        self.assertGreater(self.ticks["DELAYED_CLOSE"], 0)

    def test_all_keys_are_strings_or_ints(self):
        for key in self.ticks:
            self.assertIsInstance(key, (str, int))


@pytest.mark.integration
class TestSnapshotDelayedFrozen(unittest.TestCase):
    """
    Snapshot using DELAYED_FROZEN market data.
    Combines delayed and frozen — last available delayed price.
    Safe to run any day.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = connect_app()
        cls.app.reqMarketDataType(MarketDataType.DELAYED_FROZEN)
        cls.ticks = cls.app.request_snapshot(contract=make_spx())

    @classmethod
    def tearDownClass(cls):
        disconnect_app(cls.app)

    def test_returns_non_empty_dict(self):
        self.assertIsInstance(self.ticks, dict)
        self.assertGreater(len(self.ticks), 0)

    def test_market_data_type_key_present(self):
        self.assertIn(MARKET_DATA_TYPE_KEY, self.ticks)

    def test_market_data_type_is_delayed_frozen(self):
        self.assertEqual(self.ticks[MARKET_DATA_TYPE_KEY], MarketDataType.DELAYED_FROZEN)

    def test_delayed_close_present(self):
        self.assertIn("DELAYED_CLOSE", self.ticks)

    def test_delayed_close_is_positive(self):
        self.assertGreater(self.ticks["DELAYED_CLOSE"], 0)

    def test_all_keys_are_strings_or_ints(self):
        for key in self.ticks:
            self.assertIsInstance(key, (str, int))


@pytest.mark.integration
class TestSnapshotLive(unittest.TestCase):
    """
    Snapshot using LIVE market data.
    Requires market data subscription.
    Only run on weekdays during market hours (Mon-Fri 9:30-16:00 ET).
    """

    @classmethod
    def setUpClass(cls):
        cls.app = connect_app()
        cls.app.reqMarketDataType(MarketDataType.LIVE)
        cls.ticks = cls.app.request_snapshot(contract=make_spx())

    @classmethod
    def tearDownClass(cls):
        disconnect_app(cls.app)

    def test_returns_non_empty_dict(self):
        self.assertIsInstance(self.ticks, dict)
        self.assertGreater(len(self.ticks), 0)

    def test_market_data_type_is_live(self):
        self.assertEqual(self.ticks[MARKET_DATA_TYPE_KEY], MarketDataType.LIVE)

    def test_core_ticks_present(self):
        for tick in CORE_TICKS:
            self.assertIn(tick, self.ticks, f"Expected tick '{tick}' not found")

    def test_all_prices_positive(self):
        for tick in CORE_TICKS:
            if tick in self.ticks:
                self.assertGreater(self.ticks[tick], 0)

    def test_bid_less_than_ask(self):
        bid = self.ticks.get("BID")
        ask = self.ticks.get("ASK")
        if bid and ask:
            self.assertLess(bid, ask)

    def test_all_keys_are_strings_or_ints(self):
        for key in self.ticks:
            self.assertIsInstance(key, (str, int))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()