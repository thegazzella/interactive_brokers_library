# tests/test_regulatory_snapshot.py
#
# Tests comparing regulatory vs non-regulatory snapshot output.
#
# A regulatory snapshot (is_regulatory=True) requests an NBBO
# (National Best Bid/Offer) quote — real-time regardless of subscription
# status, but charged per request. A non-regulatory snapshot returns
# whatever the current MarketDataType is set to.
#
# Both are tested here using FROZEN so the suite is safe to run any day.
# Switch to LIVE on weekdays for a more meaningful comparison.
#
# Run:
#   python -m pytest tests/test_regulatory_snapshot.py -v -m integration

from __future__ import annotations

import threading
import time
import unittest

import pytest

from query_tws.instruments.contract import make_contract
from query_tws.market_data import MarketDataType
from query_tws.market_data.requests.snapshot import MARKET_DATA_TYPE_KEY
from query_tws.trading_app import TradingApp

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

TWS_HOST  = "127.0.0.1"
TWS_PORT  = 7497
CLIENT_ID = 12

SPX_CON_ID = 416904


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
# Integration tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRegulatoryVsNonRegulatory(unittest.TestCase):
    """
    Compares regulatory and non-regulatory snapshot output for SPX.

    Both requests use FROZEN market data so the test is safe to run
    any day without a live subscription.

    Key differences to observe:
    - Regulatory snapshots may return a different set of tick types
    - Regulatory snapshots do not fire marketDataType callback
    - CLOSE should be consistent between both since it is historical
    """

    @classmethod
    def setUpClass(cls):
        cls.app = connect_app()
        cls.app.reqMarketDataType(MarketDataType.DELAYED)
        cls.contract = make_spx()

        cls.ticks_standard = cls.app.request_snapshot(
            contract      = cls.contract,
            is_regulatory = False,
        )
        # Respect IBKR rate limit between snapshot requests
        time.sleep(1)
        cls.ticks_regulatory = cls.app.request_snapshot(
            contract      = cls.contract,
            is_regulatory = True,
        )

    @classmethod
    def tearDownClass(cls):
        disconnect_app(cls.app)

    # ------------------------------------------------------------------
    # Structural tests — both snapshots must return valid data
    # ------------------------------------------------------------------

    def test_standard_returns_non_empty_dict(self):
        self.assertIsInstance(self.ticks_standard, dict)
        self.assertGreater(len(self.ticks_standard), 0)

    def test_regulatory_returns_non_empty_dict(self):
        self.assertIsInstance(self.ticks_regulatory, dict)
        self.assertGreater(len(self.ticks_regulatory), 0)

    def test_standard_keys_are_strings_or_ints(self):
        for key in self.ticks_standard:
            self.assertIsInstance(key, (str, int))

    def test_regulatory_keys_are_strings_or_ints(self):
        for key in self.ticks_regulatory:
            self.assertIsInstance(key, (str, int))

    # ------------------------------------------------------------------
    # MarketDataType callback — only fires for non-regulatory
    # ------------------------------------------------------------------

    def test_standard_has_market_data_type_key(self):
        """Non-regulatory snapshot fires marketDataType callback."""
        self.assertIn(MARKET_DATA_TYPE_KEY, self.ticks_standard)

    def test_regulatory_has_no_market_data_type_key(self):
        """
        Regulatory snapshot does not fire marketDataType callback —
        the NBBO quote bypasses the market data type setting.
        """
        self.assertNotIn(MARKET_DATA_TYPE_KEY, self.ticks_regulatory)

    # ------------------------------------------------------------------
    # Price consistency — CLOSE is historical, must match
    # ------------------------------------------------------------------

    def test_close_present_in_standard(self):
        self.assertIn("CLOSE", self.ticks_standard)

    def test_close_present_in_regulatory(self):
        self.assertIn("CLOSE", self.ticks_regulatory)

    def test_close_prices_are_consistent(self):
        """
        CLOSE is a fixed historical value — both snapshots must agree.
        A mismatch here would indicate a data quality issue.
        """
        std_close = self.ticks_standard.get("CLOSE")
        reg_close = self.ticks_regulatory.get("CLOSE")
        if std_close and reg_close:
            self.assertAlmostEqual(std_close, reg_close, places=2)

    # ------------------------------------------------------------------
    # Price consistency — CLOSE is historical, must match
    # ------------------------------------------------------------------

    def test_close_present_in_standard(self):
        self.assertIn("LAST", self.ticks_standard)

    def test_close_present_in_regulatory(self):
        self.assertIn("LAST", self.ticks_regulatory)

    def test_last_prices_are_consistent(self):
        """
        LAST is a live value — they agree if the user has live data.
        """
        std_close = self.ticks_standard.get("LAST")
        reg_close = self.ticks_regulatory.get("LAST")
        if std_close and reg_close:
            print(f"Snapshot Last: {std_close}")
            print(f"Regulatory Snapshot Last: {reg_close}")
            
    # ------------------------------------------------------------------
    # Tick coverage comparison — print differences for inspection
    # ------------------------------------------------------------------

    def test_log_tick_coverage_difference(self):
        """
        Regulatory and non-regulatory snapshots typically return
        different sets of tick types. This test logs the difference
        for inspection — it always passes.
        """
        std_keys = set(self.ticks_standard.keys()) - {MARKET_DATA_TYPE_KEY}
        reg_keys = set(self.ticks_regulatory.keys())
        only_in_standard   = std_keys - reg_keys
        only_in_regulatory = reg_keys - std_keys
        shared             = std_keys & reg_keys
        print(f"\nShared ticks ({len(shared)}):          {sorted(str(k) for k in shared)}")
        print(f"Only in standard ({len(only_in_standard)}):   {sorted(str(k) for k in only_in_standard)}")
        print(f"Only in regulatory ({len(only_in_regulatory)}): {sorted(str(k) for k in only_in_regulatory)}")
        # Always passes — output is for inspection
        self.assertTrue(True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()