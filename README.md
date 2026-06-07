# query_tws

A Python library for interacting with the Interactive Brokers TWS API (`ibapi`).
Provides a clean, consistent, mixin-based interface for contract resolution,
market data snapshots, and order management — built on top of the official
IBKR Python API.

---

## Features

- **Instruments** — resolve any contract type (stock, option, future, forex, index, crypto, combo/BAG) via `reqContractDetails`, query option chain parameters, search symbols
- **Market data** — snapshot requests for all four market data types (live, frozen, delayed, delayed frozen), including regulatory snapshots
- **Orders** — place limit and market orders (blocking until acknowledged), cancel individual or all orders, query open and completed orders, retrieve execution history with commissions
- **Error handling** — centralised error dispatcher classifying all IBKR error codes by severity, with clean hooks per mixin
- **Consistent design** — all requests are blocking with configurable timeouts, plain dicts as return types, no custom dataclasses

---

## Prerequisites

### 1. Python
Python 3.10 or higher is required.

### 2. ibapi (IBKR Python API)
`ibapi` is **not available on PyPI** and must be installed manually:

1. Download the TWS API installer from the [IBKR API downloads page](https://www.interactivebrokers.com/en/trading/tws-updateinfo.php)
2. Run the installer — this extracts the API source
3. Navigate to the Python client directory (typically `TWS API/source/pythonclient`)
4. Install it:
   ```bash
   pip install .
   ```

### 3. TWS or IB Gateway
You need either TWS (Trader Workstation) or IB Gateway running locally with
API connections enabled:

1. Open TWS or IB Gateway
2. Go to `File → Global Configuration → API → Settings`
3. Check **Enable ActiveX and Socket Clients**
4. Set the socket port:
   - `7497` — paper trading (recommended for development)
   - `7496` — live trading
5. Optionally uncheck **Read-Only API** if you want to place orders

---

## Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/your-username/interactive_brokers_library.git
cd interactive_brokers_library
pip install -e ".[dev]"
```

The `[dev]` extra installs `pytest` for running tests.

---

## Quick Start

```python
import threading
import time

from query_tws.trading_app import TradingApp
from query_tws.instruments.contract import make_index_contract
from query_tws.market_data import MarketDataType
from query_tws.orders import make_limit_order, OrderAction

# Connect
app = TradingApp()
app.connect("127.0.0.1", 7497, clientId=1)
threading.Thread(target=app.run, daemon=True).start()

while app.orderId is None:
    time.sleep(0.1)
print(f"Connected. orderId: {app.orderId}")

# Set market data type
app.reqMarketDataType(MarketDataType.DELAYED)

# Resolve a contract
spx = app.request_contract(
    contract=make_index_contract(symbol="SPX", exchange="CBOE", currency="USD")
)
print(f"Resolved: {spx.symbol} conId={spx.conId}")

# Get a price snapshot
ticks = app.request_snapshot(contract=spx)
print(f"SPX close: {ticks.get('CLOSE')}")

# Place a limit order
from query_tws.instruments.contract import make_option_contract
call = app.request_contract(
    contract=make_option_contract(
        symbol                       = "SPX",
        lastTradeDateOrContractMonth = "20261231",
        strike                       = 5500.0,
        right                        = "C",
        tradingClass                 = "SPXW",
    )
)
order    = make_limit_order(action=OrderAction.BUY, quantity=1, price=10.0)
order_id = app.place_order(contract=call, order=order)
print(f"Order placed: orderId={order_id}")

app.disconnect()
```

---

## Library Structure

```
query_tws/
├── trading_app.py              — TradingApp: composes all mixins
│
├── errors/
│   ├── codes.py                — named error code constants
│   ├── error_codes.py          — full registry {code: (message, notes)}
│   ├── error_severity.py       — severity classification (INFO/WARNING/ERROR/CRITICAL)
│   └── dispatcher.py           — ErrorDispatcherMixin
│
├── instruments/
│   ├── contract.py             — contract factories (make_contract, make_option_contract, ...)
│   └── requests/
│       ├── contract_details.py — ContractDetailsMixin: request_contract()
│       ├── opt_params.py       — OptParamsMixin: request_opt_params()
│       └── matching_symbols.py — MatchingSymbolsMixin: request_matching_symbols()
│
├── market_data/
│   ├── const.py                — MarketDataType enum
│   └── requests/
│       └── snapshot.py         — SnapshotMixin: request_snapshot()
│
└── orders/
    ├── const.py                — OrderAction, OrderStatus, TimeInForce
    ├── order.py                — order factories (make_order, make_limit_order, ...)
    └── requests/
        ├── orders.py           — OrdersMixin: place_order(), cancel_order(), ...
        └── executions.py       — ExecutionsMixin: request_executions(), get_executions()
```

---

## Running Tests

### Unit tests (no TWS required)
```bash
python -m pytest tests/ -v -m "not integration"
```

### Integration tests (TWS must be running on port 7497)
```bash
python -m pytest tests/ -v -m integration
```

### All tests
```bash
python -m pytest tests/ -v
```

---

## Key Design Decisions

**Mixin-based architecture**
Each concern (contract resolution, market data, orders) lives in its own mixin
with a unique internal method name to avoid Python MRO conflicts. `TradingApp`
composes all mixins and owns the single `on_request_failed()` dispatcher.

**Blocking requests**
All public request methods (`request_contract`, `request_snapshot`, `place_order` etc.)
block until TWS responds or the timeout expires. This makes strategy code
straightforward to write and reason about.

**Error handling**
All IBKR error codes are classified by severity in `errors/error_severity.py`.
The dispatcher calls `on_request_failed()` for any blocking error, which
immediately unblocks the waiting request rather than waiting for the full timeout.

**No custom dataclasses**
All results are returned as raw ibapi objects or plain `dict` — consistent,
inspectable, and requiring no additional imports.

**Contract and order factories**
`make_contract()` and `make_order()` follow the same pattern — all fields are
keyword-only, optional, and named exactly as the ibapi attributes. Only
explicitly passed fields are set; everything else is left at the ibapi default.

---

## Compatibility

| Component      | Version       |
|----------------|---------------|
| Python         | >= 3.10       |
| ibapi          | >= 10.19      |
| TWS / Gateway  | >= 10.19      |

---

## License

This project is for educational and personal use. Interactive Brokers API usage
is subject to the [IB API Non-Commercial License](https://www.interactivebrokers.com/en/trading/ib-api.php).