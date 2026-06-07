# tests/test_instruments.py
#
# Integration tests for the instruments module.
# Requires a running TWS or IB Gateway instance on localhost.
#
# Setup (once)
# ------------
#   pip install -e ".[dev]"
#
# Run all tests
# -------------
#   python -m pytest tests/ -v
#
# Run unit tests only (no TWS required)
# --------------------------------------
#   python -m pytest tests/ -v -m "not integration"
#
# Run integration tests only (TWS required)
# ------------------------------------------
#   python -m pytest tests/ -v -m integration

from __future__ import annotations

import threading
import time
import unittest

import pytest

from query_tws.instruments.contract import (
    make_combo_leg,
    make_contract,
    make_crypto_contract,
    make_delta_neutral_contract,
    make_forex_contract,
    make_future_contract,
    make_index_contract,
    make_option_contract,
    make_stock_contract,
)
from query_tws.trading_app import TradingApp

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

TWS_HOST  = "127.0.0.1"
TWS_PORT  = 7497
CLIENT_ID = 1997


def connect_app() -> TradingApp:
    """Connect a TradingApp instance and block until handshake is complete."""
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


# ---------------------------------------------------------------------------
# Unit tests — contract factories (no TWS required)
# ---------------------------------------------------------------------------

class TestMakeContract(unittest.TestCase):
    """Tests for the generic make_contract() factory."""

    def test_empty_contract(self):
        """make_contract() with no args returns a bare Contract."""
        c = make_contract()
        self.assertEqual(c.symbol, "")
        self.assertEqual(c.secType, "")

    def test_fields_are_set(self):
        """Only explicitly passed fields are set."""
        c = make_contract(symbol="AAPL", secType="STK", currency="USD")
        self.assertEqual(c.symbol, "AAPL")
        self.assertEqual(c.secType, "STK")
        self.assertEqual(c.currency, "USD")

    def test_primary_exchange_smart_is_stripped(self):
        """primaryExchange='SMART' must be silently dropped."""
        c = make_contract(symbol="AAPL", primaryExchange="SMART")
        self.assertEqual(c.primaryExchange, "")

    def test_primary_exchange_non_smart_is_kept(self):
        c = make_contract(symbol="AAPL", primaryExchange="NASDAQ")
        self.assertEqual(c.primaryExchange, "NASDAQ")


class TestMakeStockContract(unittest.TestCase):

    def test_sec_type_is_stk(self):
        c = make_stock_contract(symbol="SPY", exchange="ARCA", currency="USD")
        self.assertEqual(c.secType, "STK")

    def test_fields_set_correctly(self):
        c = make_stock_contract(
            symbol          = "BMW",
            currency        = "EUR",
            exchange        = "SMART",
            primaryExchange = "IBIS",
        )
        self.assertEqual(c.symbol, "BMW")
        self.assertEqual(c.currency, "EUR")
        self.assertEqual(c.primaryExchange, "IBIS")

    def test_optional_fields_absent(self):
        """Fields not passed must remain at ibapi default (empty string)."""
        c = make_stock_contract(symbol="IBM", exchange="SMART", currency="USD")
        self.assertEqual(c.localSymbol, "")
        self.assertEqual(c.tradingClass, "")


class TestMakeIndexContract(unittest.TestCase):

    def test_sec_type_is_ind(self):
        c = make_index_contract(symbol="SPX", exchange="CBOE", currency="USD")
        self.assertEqual(c.secType, "IND")

    def test_fields_set_correctly(self):
        c = make_index_contract(symbol="DAX", exchange="EUREX", currency="EUR")
        self.assertEqual(c.symbol, "DAX")
        self.assertEqual(c.exchange, "EUREX")
        self.assertEqual(c.currency, "EUR")


class TestMakeOptionContract(unittest.TestCase):

    def test_sec_type_is_opt(self):
        c = make_option_contract(
            symbol                       = "GOOG",
            lastTradeDateOrContractMonth = "20260620",
            strike                       = 1180.0,
            right                        = "C",
            currency                     = "USD",
            exchange                     = "SMART",
            multiplier                   = "100",
        )
        self.assertEqual(c.secType, "OPT")

    def test_right_is_normalised_to_uppercase(self):
        c = make_option_contract(strike=100.0, right="c")
        self.assertEqual(c.right, "C")

    def test_invalid_right_raises(self):
        with self.assertRaises(ValueError):
            make_option_contract(strike=100.0, right="X")

    def test_invalid_expiry_format_raises(self):
        with self.assertRaises(ValueError):
            make_option_contract(
                strike                       = 100.0,
                lastTradeDateOrContractMonth = "2026-06-20",
            )

    def test_expiry_yyyymm_raises(self):
        """Options require YYYYMMDD — YYYYMM should be rejected."""
        with self.assertRaises(ValueError):
            make_option_contract(
                strike                       = 100.0,
                lastTradeDateOrContractMonth = "202606",
            )

    def test_strike_is_optional(self):
        """strike=None must not raise — partial contracts are valid for queries."""
        c = make_option_contract(symbol="FISV", exchange="SMART", currency="USD")
        # ibapi initialises uninitialised strike to float max, not 0.0
        self.assertEqual(c.strike, 1.7976931348623157e+308)
    
    def test_trading_class_set(self):
        c = make_option_contract(
            symbol                       = "SPX",
            lastTradeDateOrContractMonth = "20260604",
            strike                       = 5500.0,
            right                        = "C",
            tradingClass                 = "SPXW",
        )
        self.assertEqual(c.tradingClass, "SPXW")


class TestMakeFutureContract(unittest.TestCase):

    def test_sec_type_is_fut(self):
        c = make_future_contract(
            symbol                       = "ES",
            lastTradeDateOrContractMonth = "202509",
            exchange                     = "CME",
            currency                     = "USD",
        )
        self.assertEqual(c.secType, "FUT")

    def test_expiry_yyyymm_accepted(self):
        c = make_future_contract(
            symbol                       = "ES",
            lastTradeDateOrContractMonth = "202509",
            exchange                     = "CME",
            currency                     = "USD",
        )
        self.assertEqual(c.lastTradeDateOrContractMonth, "202509")

    def test_expiry_yyyymmdd_accepted(self):
        c = make_future_contract(
            symbol                       = "ES",
            lastTradeDateOrContractMonth = "20250919",
            exchange                     = "CME",
            currency                     = "USD",
        )
        self.assertEqual(c.lastTradeDateOrContractMonth, "20250919")

    def test_invalid_expiry_raises(self):
        with self.assertRaises(ValueError):
            make_future_contract(
                symbol                       = "ES",
                lastTradeDateOrContractMonth = "2025-09",
                exchange                     = "CME",
                currency                     = "USD",
            )


class TestMakeForexContract(unittest.TestCase):

    def test_sec_type_is_cash(self):
        c = make_forex_contract(symbol="EUR", currency="GBP")
        self.assertEqual(c.secType, "CASH")

    def test_exchange_is_always_idealpro(self):
        c = make_forex_contract(symbol="EUR", currency="USD")
        self.assertEqual(c.exchange, "IDEALPRO")


class TestMakeCryptoContract(unittest.TestCase):

    def test_sec_type_is_crypto(self):
        c = make_crypto_contract(symbol="ETH", currency="USD")
        self.assertEqual(c.secType, "CRYPTO")

    def test_exchange_is_always_paxos(self):
        c = make_crypto_contract(symbol="BTC", currency="USD")
        self.assertEqual(c.exchange, "PAXOS")


class TestMakeComboLeg(unittest.TestCase):

    def test_action_normalised_to_uppercase(self):
        leg = make_combo_leg(conId=123, ratio=1, action="buy", exchange="SMART")
        self.assertEqual(leg.action, "BUY")

    def test_invalid_action_raises(self):
        with self.assertRaises(ValueError):
            make_combo_leg(conId=123, ratio=1, action="HOLD", exchange="SMART")

    def test_invalid_ratio_raises(self):
        with self.assertRaises(ValueError):
            make_combo_leg(conId=123, ratio=0, action="BUY", exchange="SMART")

    def test_short_sale_slot_without_short_raises(self):
        with self.assertRaises(ValueError):
            make_combo_leg(
                conId=123, ratio=1, action="BUY",
                exchange="SMART", shortSaleSlot=1,
            )

    def test_designated_location_without_slot_2_raises(self):
        with self.assertRaises(ValueError):
            make_combo_leg(
                conId=123, ratio=1, action="SHORT", exchange="SMART",
                shortSaleSlot=1, designatedLocation="SOMEWHERE",
            )


class TestMakeDeltaNeutralContract(unittest.TestCase):

    def test_fields_set_correctly(self):
        dnc = make_delta_neutral_contract(conId=265598, delta=0.5, price=185.0)
        self.assertEqual(dnc.conId, 265598)
        self.assertEqual(dnc.delta, 0.5)
        self.assertEqual(dnc.price, 185.0)

    def test_invalid_delta_raises(self):
        with self.assertRaises(ValueError):
            make_delta_neutral_contract(delta=1.5)

    def test_invalid_price_raises(self):
        with self.assertRaises(ValueError):
            make_delta_neutral_contract(price=-10.0)

    def test_returns_dnc_not_dncs(self):
        """Regression test for the dncs typo bug."""
        dnc = make_delta_neutral_contract(conId=1, delta=0.5, price=10.0)
        self.assertIsNotNone(dnc)


# ---------------------------------------------------------------------------
# Integration tests — require live TWS connection
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRequestContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = connect_app()

    @classmethod
    def tearDownClass(cls):
        disconnect_app(cls.app)

    def test_resolve_spx_index(self):
        """SPX index contract resolves with a valid conId."""
        contract = make_index_contract(symbol="SPX", exchange="CBOE", currency="USD")
        resolved = self.app.request_contract(contract=contract)
        self.assertEqual(resolved.symbol, "SPX")
        self.assertEqual(resolved.secType, "IND")
        self.assertGreater(resolved.conId, 0)

    def test_resolve_spy_stock(self):
        """SPY stock resolves correctly on ARCA."""
        contract = make_stock_contract(symbol="SPY", exchange="ARCA", currency="USD")
        resolved = self.app.request_contract(contract=contract)
        self.assertEqual(resolved.symbol, "SPY")
        self.assertEqual(resolved.secType, "STK")
        self.assertGreater(resolved.conId, 0)

    def test_resolve_es_future(self):
        """ES front-month future resolves correctly on CME."""
        contract = make_future_contract(
            symbol                       = "ES",
            lastTradeDateOrContractMonth = "202612",
            exchange                     = "CME",
            currency                     = "USD",
        )
        resolved = self.app.request_contract(contract=contract)
        self.assertEqual(resolved.symbol, "ES")
        self.assertEqual(resolved.secType, "FUT")
        self.assertGreater(resolved.conId, 0)

    def test_resolve_eur_usd_forex(self):
        """EUR.USD forex pair resolves on IDEALPRO."""
        contract = make_forex_contract(symbol="EUR", currency="USD")
        resolved = self.app.request_contract(contract=contract)
        self.assertEqual(resolved.symbol, "EUR")
        self.assertEqual(resolved.secType, "CASH")
        self.assertGreater(resolved.conId, 0)

    def test_invalid_symbol_raises_value_error(self):
        """An unrecognised symbol must raise ValueError, not hang."""
        contract = make_stock_contract(
            symbol   = "XXXX_INVALID",
            exchange = "SMART",
            currency = "USD",
        )
        with self.assertRaises(ValueError):
            self.app.request_contract(contract=contract)


@pytest.mark.integration
class TestRequestOptParams(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = connect_app()
        spx_raw = make_index_contract(symbol="SPX", exchange="CBOE", currency="USD")
        cls.spx = cls.app.request_contract(contract=spx_raw)

    @classmethod
    def tearDownClass(cls):
        disconnect_app(cls.app)

    def test_returns_non_empty_list(self):
        chain = self.app.request_opt_params(
            underlying_symbol   = self.spx.symbol,
            fut_fop_exchange    = "",
            underlying_sec_type = self.spx.secType,
            underlying_con_id   = self.spx.conId,
        )
        self.assertIsInstance(chain, list)
        self.assertGreater(len(chain), 0)

    def test_each_entry_has_required_keys(self):
        chain = self.app.request_opt_params(
            underlying_symbol   = self.spx.symbol,
            fut_fop_exchange    = "",
            underlying_sec_type = self.spx.secType,
            underlying_con_id   = self.spx.conId,
        )
        required_keys = {
            "exchange", "underlyingConId", "tradingClass",
            "multiplier", "expirations", "strikes",
        }
        for entry in chain:
            self.assertEqual(required_keys, set(entry.keys()))

    def test_expirations_and_strikes_non_empty(self):
        chain = self.app.request_opt_params(
            underlying_symbol   = self.spx.symbol,
            fut_fop_exchange    = "",
            underlying_sec_type = self.spx.secType,
            underlying_con_id   = self.spx.conId,
        )
        for entry in chain:
            self.assertGreater(len(entry["expirations"]), 0)
            self.assertGreater(len(entry["strikes"]), 0)

    def test_underlying_con_id_matches(self):
        chain = self.app.request_opt_params(
            underlying_symbol   = self.spx.symbol,
            fut_fop_exchange    = "",
            underlying_sec_type = self.spx.secType,
            underlying_con_id   = self.spx.conId,
        )
        for entry in chain:
            self.assertEqual(entry["underlyingConId"], self.spx.conId)


@pytest.mark.integration
class TestRequestMatchingSymbols(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = connect_app()

    @classmethod
    def tearDownClass(cls):
        disconnect_app(cls.app)

    def test_returns_non_empty_list(self):
        results = self.app.request_matching_symbols(pattern="SPY")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_each_result_has_contract(self):
        results = self.app.request_matching_symbols(pattern="SPY")
        for cd in results:
            self.assertIsNotNone(cd.contract)
            self.assertIsInstance(cd.contract, Contract)
            self.assertGreater(len(cd.contract.symbol), 0)
        
    def test_results_capped_at_16(self):
        """IBKR returns at most 16 results."""
        results = self.app.request_matching_symbols(pattern="S")
        self.assertGreater(len(results), 0)
    
    def test_invalid_pattern_raises_value_error(self):
        """A pattern with no matches must raise ValueError."""
        with self.assertRaises(ValueError):
            self.app.request_matching_symbols(pattern="ZZZZZZZZZZZZZ")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()