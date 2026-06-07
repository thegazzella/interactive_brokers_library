# instruments/contract.py

from __future__ import annotations

from ibapi.contract import ComboLeg, Contract, DeltaNeutralContract


# ---------------------------------------------------------------------------
# make_contract — single construction point, all attributes optional
# ---------------------------------------------------------------------------

def make_contract(
    *,
    conId:                          int                  | None = None,
    symbol:                         str                  | None = None,
    secType:                        str                  | None = None,
    lastTradeDateOrContractMonth:   str                  | None = None,
    lastTradeDate:                  str                  | None = None,
    strike:                         float                | None = None,
    right:                          str                  | None = None,
    multiplier:                     str                  | None = None,
    exchange:                       str                  | None = None,
    primaryExchange:                str                  | None = None,
    currency:                       str                  | None = None,
    localSymbol:                    str                  | None = None,
    tradingClass:                   str                  | None = None,
    includeExpired:                 bool                 | None = None,
    secIdType:                      str                  | None = None,
    secId:                          str                  | None = None,
    description:                    str                  | None = None,
    issuerId:                       str                  | None = None,
    comboLegsDescrip:               str                  | None = None,
    comboLegs:                      list[ComboLeg]       | None = None,
    deltaNeutralContract:           DeltaNeutralContract | None = None,
) -> Contract:
    """
    General-purpose Contract factory. All parameters are optional and
    named exactly as the ibapi Contract attributes. Only fields explicitly
    passed are set — everything else is left at the ibapi default.

    Tradable secTypes
    -----------------
    STK   : Stock
    BOND  : Bond
    FUND  : Mutual Fund
    IND   : Index
    CMDTY : Commodity
    CASH  : Forex Pair
    CRYPTO: Cryptocurrency
    FUT   : Future
    OPT   : Option
    FOP   : Option on Future
    WAR   : Warrant
    BAG   : Combo / Spread

    Non-tradable
    ------------
    NEWS  : News feed
    """
    c = Contract()

    # primaryExchange must never be "SMART" — IBKR silently misbehaves if set
    if primaryExchange == "SMART":
        primaryExchange = None

    if conId                        is not None: c.conId                        = conId
    if symbol                       is not None: c.symbol                       = symbol
    if secType                      is not None: c.secType                      = secType
    if lastTradeDateOrContractMonth is not None: c.lastTradeDateOrContractMonth = lastTradeDateOrContractMonth
    if lastTradeDate                is not None: c.lastTradeDate                = lastTradeDate
    if strike                       is not None: c.strike                       = strike
    if right                        is not None: c.right                        = right
    if multiplier                   is not None: c.multiplier                   = multiplier
    if exchange                     is not None: c.exchange                     = exchange
    if primaryExchange              is not None: c.primaryExchange              = primaryExchange
    if currency                     is not None: c.currency                     = currency
    if localSymbol                  is not None: c.localSymbol                  = localSymbol
    if tradingClass                 is not None: c.tradingClass                 = tradingClass
    if includeExpired               is not None: c.includeExpired               = includeExpired
    if secIdType                    is not None: c.secIdType                    = secIdType
    if secId                        is not None: c.secId                        = secId
    if description                  is not None: c.description                  = description
    if issuerId                     is not None: c.issuerId                     = issuerId
    if comboLegsDescrip             is not None: c.comboLegsDescrip             = comboLegsDescrip
    if comboLegs                    is not None: c.comboLegs                    = comboLegs
    if deltaNeutralContract         is not None: c.deltaNeutralContract         = deltaNeutralContract
    return c


# ---------------------------------------------------------------------------
# make_stock_contract — equities
# ---------------------------------------------------------------------------

def make_stock_contract(
    *,
    symbol:          str | None = None,
    currency:        str | None = None,
    exchange:        str | None = None,
    primaryExchange: str | None = None,
    localSymbol:     str | None = None,
    tradingClass:    str | None = None,
    secIdType:       str | None = None,
    secId:           str | None = None,
) -> Contract:
    """
    Convenience factory for equity contracts (secType='STK').

    Optional
    --------
    symbol          : ticker e.g. "AAPL", "UCG"
    currency        : e.g. "USD", "EUR"
    exchange        : e.g. "SMART"
    primaryExchange : e.g. "NASDAQ", "BVME" — set to avoid ambiguity
    localSymbol     : IB local symbol if known
    tradingClass    : IB trading class if needed
    secIdType       : "CUSIP", "SEDOL", "ISIN", "RIC"
    secId           : value for secIdType
    """
    return make_contract(
        secType         = "STK",
        symbol          = symbol,
        currency        = currency,
        exchange        = exchange,
        primaryExchange = primaryExchange,
        localSymbol     = localSymbol,
        tradingClass    = tradingClass,
        secIdType       = secIdType,
        secId           = secId,
    )


# ---------------------------------------------------------------------------
# make_index_contract — indices (market data only, not directly tradeable)
# ---------------------------------------------------------------------------

def make_index_contract(
    *,
    symbol:   str | None = None,
    exchange: str | None = None,
    currency: str | None = None,
) -> Contract:
    """
    Convenience factory for index contracts (secType='IND').
    Use for market data requests (e.g. SPX spot price).
    Indices are not directly tradeable — use OPT or FUT on top.

    Optional
    --------
    symbol   : index symbol e.g. "SPX", "VIX", "INDU", "NDX"
    exchange : primary exchange e.g. "CBOE" for SPX, "NYSE" for INDU
    currency : e.g. "USD"

    Example
    -------
    make_index_contract(symbol="SPX", exchange="CBOE", currency="USD")
    """
    return make_contract(
        secType  = "IND",
        symbol   = symbol,
        exchange = exchange,
        currency = currency,
    )


# ---------------------------------------------------------------------------
# make_option_contract — equity / index options
# ---------------------------------------------------------------------------

def make_option_contract(
    *,
    symbol:                         str   | None = None,
    lastTradeDateOrContractMonth:   str   | None = None,
    strike:                         float | None = None,
    right:                          str   | None = None,
    currency:                       str   | None = None,
    exchange:                       str   | None = None,
    primaryExchange:                str   | None = None,
    multiplier:                     str   | None = None,
    tradingClass:                   str   | None = None,
    localSymbol:                    str   | None = None,
    includeExpired:                 bool  | None = None,
) -> Contract:
    """
    Convenience factory for option contracts (secType='OPT').

    Optional
    --------
    symbol                       : underlying ticker e.g. "SPX", "AAPL"
    lastTradeDateOrContractMonth : expiry in YYYYMMDD e.g. "20251219"
    strike                       : strike price e.g. 5800.0
    right                        : "C" for call, "P" for put
    currency                     : e.g. "USD"
    exchange                     : e.g. "SMART"
    primaryExchange              : e.g. "CBOE" for SPX options
    multiplier                   : e.g. "100" for standard equity options
    tradingClass                 : e.g. "SPXW" for SPX weeklies
    localSymbol                  : IB local symbol if known
    includeExpired               : True to include expired contracts
    """
    # --- validation ---
    if right is not None:
        right = right.upper()
        if right not in ("C", "P"):
            raise ValueError(f"right must be 'C' or 'P', got '{right}'")

    if lastTradeDateOrContractMonth is not None:
        if (
            not lastTradeDateOrContractMonth.isdigit()
            or len(lastTradeDateOrContractMonth) != 8
        ):
            raise ValueError(
                f"lastTradeDateOrContractMonth must be YYYYMMDD, "
                f"got '{lastTradeDateOrContractMonth}'"
            )

    return make_contract(
        secType                      = "OPT",
        symbol                       = symbol,
        lastTradeDateOrContractMonth = lastTradeDateOrContractMonth,
        strike                       = strike,
        right                        = right,
        currency                     = currency,
        exchange                     = exchange,
        primaryExchange              = primaryExchange,
        multiplier                   = multiplier,
        tradingClass                 = tradingClass,
        localSymbol                  = localSymbol,
        includeExpired               = includeExpired,
    )


# ---------------------------------------------------------------------------
# make_future_contract — futures
# ---------------------------------------------------------------------------

def make_future_contract(
    *,
    symbol:                         str  | None = None,
    lastTradeDateOrContractMonth:   str  | None = None,
    exchange:                       str  | None = None,
    currency:                       str  | None = None,
    multiplier:                     str  | None = None,
    localSymbol:                    str  | None = None,
    tradingClass:                   str  | None = None,
    includeExpired:                 bool | None = None,
) -> Contract:
    """
    Convenience factory for futures contracts (secType='FUT').

    Optional
    --------
    symbol                       : ticker e.g. "ES", "NQ"
    lastTradeDateOrContractMonth : expiry in YYYYMMDD or YYYYMM e.g. "202512"
    exchange                     : e.g. "CME", "NYMEX"
    currency                     : e.g. "USD"
    multiplier                   : contract multiplier e.g. "50" for ES
    localSymbol                  : IB local symbol if known
    tradingClass                 : IB trading class if needed
    includeExpired               : True to include expired contracts
    """
    if lastTradeDateOrContractMonth is not None:
        if (
            not lastTradeDateOrContractMonth.isdigit()
            or len(lastTradeDateOrContractMonth) not in (6, 8)
        ):
            raise ValueError(
                f"lastTradeDateOrContractMonth must be YYYYMM or YYYYMMDD, "
                f"got '{lastTradeDateOrContractMonth}'"
            )

    return make_contract(
        secType                      = "FUT",
        symbol                       = symbol,
        lastTradeDateOrContractMonth = lastTradeDateOrContractMonth,
        exchange                     = exchange,
        currency                     = currency,
        multiplier                   = multiplier,
        localSymbol                  = localSymbol,
        tradingClass                 = tradingClass,
        includeExpired               = includeExpired,
    )


# ---------------------------------------------------------------------------
# make_forex_contract — forex pairs
# ---------------------------------------------------------------------------

def make_forex_contract(
    *,
    symbol:   str | None = None,
    currency: str | None = None,
) -> Contract:
    """
    Convenience factory for forex pairs (secType='CASH').
    Exchange is always 'IDEALPRO' — IB's only forex routing exchange.

    Optional
    --------
    symbol   : base currency e.g. "EUR"
    currency : quote currency e.g. "USD"

    Example
    -------
    make_forex_contract(symbol="EUR", currency="USD")
    """
    return make_contract(
        secType  = "CASH",
        exchange = "IDEALPRO",
        symbol   = symbol,
        currency = currency,
    )


# ---------------------------------------------------------------------------
# make_crypto_contract — cryptocurrency
# ---------------------------------------------------------------------------

def make_crypto_contract(
    *,
    symbol:   str | None = None,
    currency: str | None = None,
) -> Contract:
    """
    Convenience factory for crypto contracts (secType='CRYPTO').
    Exchange is always 'PAXOS' — IB's crypto exchange.

    Optional
    --------
    symbol   : base currency e.g. "ETH", "BTC"
    currency : quote currency e.g. "USD"

    Example
    -------
    make_crypto_contract(symbol="ETH", currency="USD")
    """
    return make_contract(
        secType  = "CRYPTO",
        exchange = "PAXOS",
        symbol   = symbol,
        currency = currency,
    )


# ---------------------------------------------------------------------------
# make_combo_leg — ComboLeg for BAG contracts
# ---------------------------------------------------------------------------

def make_combo_leg(
    *,
    conId:              int | None = None,
    ratio:              int | None = None,
    action:             str | None = None,   # "BUY", "SELL", "SHORT"
    exchange:           str | None = None,
    openClose:          int | None = None,   # SAME_POS=0, OPEN_POS=1, CLOSE_POS=2, UNKNOWN_POS=3
    shortSaleSlot:      int | None = None,   # 1=IB, 2=third party — only for SHORT
    designatedLocation: str | None = None,   # required when shortSaleSlot=2
    exemptCode:         int | None = None,   # -1 = not exempt
) -> ComboLeg:
    """
    Factory for ComboLeg objects used in BAG (combo) contracts.

    Optional
    --------
    conId              : resolved conId of the leg
    ratio              : number of units for this leg e.g. 1
    action             : "BUY", "SELL", or "SHORT"
    exchange           : routing exchange e.g. "SMART"
    openClose          : SAME_POS=0, OPEN_POS=1, CLOSE_POS=2, UNKNOWN_POS=3
    shortSaleSlot      : 1=IB locates, 2=third party — only for SHORT
    designatedLocation : required when shortSaleSlot=2
    exemptCode         : short sale exemption code, -1 if not exempt
    """
    # --- validation ---
    if action is not None:
        action = action.upper()
        if action not in ("BUY", "SELL", "SHORT"):
            raise ValueError(f"action must be 'BUY', 'SELL', or 'SHORT', got '{action}'")
    if ratio is not None and ratio <= 0:
        raise ValueError(f"ratio must be positive, got {ratio}")
    if shortSaleSlot is not None and action is not None and action != "SHORT":
        raise ValueError("shortSaleSlot is only valid when action='SHORT'")
    if designatedLocation is not None and shortSaleSlot is not None and shortSaleSlot != 2:
        raise ValueError("designatedLocation is only required when shortSaleSlot=2")

    # --- construction ---
    leg = ComboLeg()
    if conId              is not None: leg.conId              = conId
    if ratio              is not None: leg.ratio              = ratio
    if action             is not None: leg.action             = action
    if exchange           is not None: leg.exchange           = exchange
    if openClose          is not None: leg.openClose          = openClose
    if shortSaleSlot      is not None: leg.shortSaleSlot      = shortSaleSlot
    if designatedLocation is not None: leg.designatedLocation = designatedLocation
    if exemptCode         is not None: leg.exemptCode         = exemptCode
    return leg


# ---------------------------------------------------------------------------
# make_delta_neutral_contract — delta hedge attachment
# ---------------------------------------------------------------------------

def make_delta_neutral_contract(
    *,
    conId: int   | None = None,
    delta: float | None = None,
    price: float | None = None,
) -> DeltaNeutralContract:
    """
    Factory for DeltaNeutralContract — used to attach a delta hedge
    to a combo order (e.g. hedge an option leg with the underlying).

    Optional
    --------
    conId : conId of the delta neutral instrument e.g. the underlying stock
    delta : delta value for the hedge e.g. 0.5
    price : price of the delta neutral instrument

    Example
    -------
    dnc = make_delta_neutral_contract(conId=265598, delta=0.5, price=185.0)
    contract = make_contract(..., deltaNeutralContract=dnc)
    """
    # --- validation ---
    if delta is not None and not -1.0 <= delta <= 1.0:
        raise ValueError(f"delta must be between -1.0 and 1.0, got {delta}")
    if price is not None and price <= 0:
        raise ValueError(f"price must be positive, got {price}")

    # --- construction ---
    dnc = DeltaNeutralContract()
    if conId is not None: dnc.conId = conId
    if delta is not None: dnc.delta = delta
    if price is not None: dnc.price = price
    return dnc