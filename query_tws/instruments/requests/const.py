# instruments/requests/const.py
#
# Shared constants for all request mixins.

from __future__ import annotations

# Default timeout in seconds for all blocking TWS requests
_CONTRACT_REQUEST_TIMEOUT:        float = 10.0
_OPT_PARAMS_REQUEST_TIMEOUT:      float = 10.0
_MATCHING_SYMBOLS_REQUEST_TIMEOUT: float = 10.0