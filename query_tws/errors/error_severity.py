# errors/error_severity.py
#
# Severity classification for all IBKR TWS API error codes.
# This is the single source of truth for how each code should be treated.
# dispatcher.py uses these sets to decide what action to take.

from __future__ import annotations

from enum import IntEnum


class ErrorSeverity(IntEnum):
    """How a given IBKR error code should be treated by the application."""
    INFO     = 0   # connectivity notifications — log only, never actionable
    WARNING  = 1   # non-fatal — operation may still succeed
    ERROR    = 2   # request failed — caller should be unblocked and notified
    CRITICAL = 3   # connection-level — may require reconnect


# ---------------------------------------------------------------------------
# INFO — log only, never unblock requests
# ---------------------------------------------------------------------------

INFO_ONLY_CODES: frozenset[int] = frozenset({
    1102,   # connectivity restored — data maintained, no action needed
    2104,   # market data farm connection OK
    2106,   # historical data farm connected
    2107,   # historical data farm inactive — available on demand
    2108,   # market data farm dormant — available on demand
    2109,   # outsideRth flag ignored — order still processed
    2111,   # algo order time adjusted to next trading date
    2119,   # market data farm connecting
    2130,   # products trading on currency price with factor
    2152,   # market depth smart depth exchanges
    2158,   # sec-def data farm connection OK
    2174,   # datetime without timezone — undocumented, observed in practice
    10233,  # defaults inherited from CASH preset
    10310,  # solicited field informational
    10331,  # any stop warning
    10332,  # cryptocurrency volatility warning
    10333,  # option exercise at-the-money warning
    10334,  # confirm omnibus order account
})

# ---------------------------------------------------------------------------
# WARNING — non-fatal, do NOT unblock requests
# ---------------------------------------------------------------------------

WARNING_ONLY_CODES: frozenset[int] = frozenset({
    # Order warnings
    161,    # cancel attempted when order not cancellable
    164,    # no market data to check price violations
    202,    # order cancelled — expected flow
    404,    # shares not available for short sale — order held
    481,    # order size reduced
    # Market data warnings
    300,    # can't find EId with ticker — benign cancel attempt
    301,    # invalid ticker action
    316,    # market depth halted — re-subscribe
    317,    # market depth reset
    354,    # not subscribed — delayed data fallback available
    365,    # no scanner subscription found
    366,    # no historical data query found
    420,    # invalid real-time query — pacing violation
    # TWS notification warnings (2xxx)
    2100,   # account data subscription overridden
    2101,   # unable to subscribe — different account
    2102,   # unable to modify — still processing
    2103,   # market data farm disconnected
    2105,   # historical data farm disconnected
    2110,   # TWS-server connectivity broken — auto-restoring
    2137,   # cross side warning
    2168,   # EtradeOnly not supported
    2169,   # firmQuoteOnly not supported
    # Extended warnings
    10018,  # orders use EV warning
    10019,  # trades use EV warning
    10090,  # part of market data not subscribed
    10197,  # no market data during competing session
    10225,  # bust event — resubscribe
    10230,  # unsaved FA changes
    10231,  # groups/profiles contain invalid accounts
    10234,  # decision maker field required
    10235,  # decision maker field required (ibbot)
    10239,  # order affects flagged accounts
    10311,  # direct routing warning
    10329,  # direct routing warning
    10335,  # order presets cannot be applied
    10347,  # limited liquidity warning
})

# ---------------------------------------------------------------------------
# CONNECTION — connection-level, may require reconnect
# ---------------------------------------------------------------------------

CONNECTION_CODES: frozenset[int] = frozenset({
    # Connectivity lost/restored with data loss (requires resubscribe)
    1100,   # connectivity between IB and TWS lost
    1101,   # connectivity restored — data lost, re-submit all subscriptions
    1300,   # TWS socket port reset — reconnect required
    # Client-side connection errors
    501,    # already connected
    502,    # couldn't connect to TWS
    503,    # TWS out of date
    504,    # not connected
    505,    # fatal error: unknown message id
    506,    # unsupported version
    507,    # bad message length — EOF on socket
    508,    # bad message
    509,    # exception reading socket
    520,    # failed to create socket
    586,    # failed to read message — not connected
    # Sending errors (500-589) — connectivity failures
    510, 511, 512, 513, 514, 515, 516, 517, 518, 519,
    521, 522, 523, 524, 525, 526, 527, 528, 529, 530,
    531, 532, 533, 534, 535, 536, 537, 538, 539, 540,
    541, 542, 543, 544, 545, 546, 547, 548, 549, 550,
    551, 552, 553, 554, 555, 556, 557, 558, 559, 560,
    561, 562, 563, 564, 565, 566, 567, 568, 569, 570,
    571, 572, 573, 574, 575, 576, 577, 578, 579, 580,
    581, 582, 583, 584, 585, 587, 588, 589,
})

# ---------------------------------------------------------------------------
# ERROR — request failed, must unblock the caller
# ---------------------------------------------------------------------------

ERROR_CODES_SET: frozenset[int] = frozenset({
    # Order errors
    100, 101, 102, 103, 104, 105, 106, 107, 109, 110, 111, 113, 114, 115,
    116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 129, 131, 132,
    133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146,
    147, 148, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 162, 163,
    165, 166, 167, 168,
    # Contract errors
    200, 201, 203,
    # Market data / depth errors
    302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315,
    319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332,
    333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346,
    347, 348, 349, 350, 351, 352, 353, 355, 356, 357, 358, 359, 360, 361,
    362, 363, 364, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377,
    378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391,
    392, 393, 394, 395, 396, 397, 398, 399,
    400, 401, 402, 403, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414,
    415, 416, 417, 418, 419, 421, 422, 423, 424, 425, 426, 427, 428, 429,
    430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443,
    444, 445, 446, 447, 448, 449,
    # Extended errors
    10000, 10001, 10002, 10003, 10005, 10006, 10007, 10008, 10009, 10010,
    10011, 10012, 10013, 10014, 10015, 10016, 10017, 10020, 10021, 10022,
    10023, 10024, 10025, 10026, 10027,
    10089, 10091,
    10147, 10148,
    10186, 10187, 10189,
    10236, 10237, 10238, 10240, 10241, 10242, 10243, 10244, 10245, 10246,
    10247, 10248, 10249, 10250, 10251, 10252, 10253, 10254,
    10268, 10269, 10270,
    10276, 10277, 10278, 10279, 10280, 10281, 10282, 10283, 10284, 10285,
    10286, 10287, 10288, 10289, 10290, 10291, 10292, 10293, 10294, 10295,
    10296, 10297, 10298, 10299, 10300, 10301, 10302, 10303, 10304, 10305,
    10306, 10307, 10308, 10309, 10312, 10314, 10315, 10316, 10317, 10318,
    10319, 10321, 10322, 10324, 10325, 10326, 10327, 10328, 10330, 10336,
    10337, 10338, 10339, 10340, 10341, 10342, 10343, 10344, 10345, 10346,
})

# ---------------------------------------------------------------------------
# REQUEST_BLOCKING_CODES
# Codes that must unblock a pending request immediately.
# = all ERROR_CODES_SET + CONNECTION_CODES
# + the specific warnings that surface failure to the caller
# ---------------------------------------------------------------------------

# Warnings that are non-fatal in general but still mean the specific
# request failed — the caller needs to be unblocked and notified
_BLOCKING_WARNINGS: frozenset[int] = frozenset({
    354,    # not subscribed — caller needs to know to switch to delayed
    366,    # no historical data — request failed
    420,    # pacing violation — request failed
    10090,  # partial subscription — caller may need to act
    10148,  # order already filled — cancel failed
})

REQUEST_BLOCKING_CODES: frozenset[int] = (
    ERROR_CODES_SET
    | CONNECTION_CODES
    | _BLOCKING_WARNINGS
)


# ---------------------------------------------------------------------------
# Lookup helper — classify a single error code
# ---------------------------------------------------------------------------

def classify(errorCode: int) -> ErrorSeverity:
    """
    Return the ErrorSeverity for a given IBKR error code.
    Falls back to ErrorSeverity.ERROR for unknown codes.

    Args:
        errorCode: Numeric error code from TradingApp.error().

    Returns:
        ErrorSeverity enum value.
    """
    if errorCode in INFO_ONLY_CODES:
        return ErrorSeverity.INFO
    if errorCode in WARNING_ONLY_CODES:
        return ErrorSeverity.WARNING
    if errorCode in CONNECTION_CODES:
        return ErrorSeverity.CRITICAL
    if errorCode in ERROR_CODES_SET:
        return ErrorSeverity.ERROR
    # Unknown codes — treat as ERROR to avoid silently swallowing them
    return ErrorSeverity.ERROR