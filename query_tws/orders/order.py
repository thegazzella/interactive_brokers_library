# orders/order.py
#
# Order factory functions.
# Mirrors the pattern in instruments/contract.py — one general make_order()
# function that sets only explicitly passed fields, plus convenience factories
# for common order types.
#
# All parameters are keyword-only and optional. None means "leave the ibapi
# default untouched" — callers never need to know about UNSET_DOUBLE etc.
#
# Usage:
#   from orders.order import make_order, make_limit_order, make_market_order
#
#   # Convenience factories
#   order = make_limit_order(action=OrderAction.BUY, quantity=1, price=5500.0)
#   order = make_market_order(action=OrderAction.SELL, quantity=1)
#
#   # General factory for anything else
#   order = make_order(
#       action    = "BUY",
#       orderType = "TRAIL",
#       totalQuantity = 1,
#       trailStopPrice = 5400.0,
#       tif       = "GTC",
#   )
#
#   # Place via TradingApp
#   order_id = app.place_order(contract=resolved, order=order)

from __future__ import annotations

from decimal import Decimal

from ibapi.order import Order

from .const import OrderAction, TimeInForce


# ---------------------------------------------------------------------------
# make_order — single construction point, all attributes optional
# ---------------------------------------------------------------------------

def make_order(
    *,
    # --- main order fields ---
    action:                             str          | None = None,
    totalQuantity:                      Decimal      | None = None,
    orderType:                          str          | None = None,
    lmtPrice:                           float        | None = None,
    auxPrice:                           float        | None = None,
    # --- extended order fields ---
    tif:                                str          | None = None,
    activeStartTime:                    str          | None = None,
    activeStopTime:                     str          | None = None,
    ocaGroup:                           str          | None = None,
    ocaType:                            int          | None = None,
    orderRef:                           str          | None = None,
    transmit:                           bool         | None = None,
    parentId:                           int          | None = None,
    blockOrder:                         bool         | None = None,
    sweepToFill:                        bool         | None = None,
    displaySize:                        int          | None = None,
    triggerMethod:                      int          | None = None,
    outsideRth:                         bool         | None = None,
    hidden:                             bool         | None = None,
    goodAfterTime:                      str          | None = None,
    goodTillDate:                       str          | None = None,
    rule80A:                            str          | None = None,
    allOrNone:                          bool         | None = None,
    minQty:                             int          | None = None,
    percentOffset:                      float        | None = None,
    overridePercentageConstraints:      bool         | None = None,
    trailStopPrice:                     float        | None = None,
    trailingPercent:                    float        | None = None,
    # --- financial advisors only ---
    faGroup:                            str          | None = None,
    faMethod:                           str          | None = None,
    faPercentage:                       str          | None = None,
    # --- institutional only ---
    designatedLocation:                 str          | None = None,
    openClose:                          str          | None = None,
    origin:                             int          | None = None,
    shortSaleSlot:                      int          | None = None,
    exemptCode:                         int          | None = None,
    # --- SMART routing only ---
    discretionaryAmt:                   float        | None = None,
    optOutSmartRouting:                 bool         | None = None,
    # --- BOX exchange orders only ---
    auctionStrategy:                    int          | None = None,
    startingPrice:                      float        | None = None,
    stockRefPrice:                      float        | None = None,
    delta:                              float        | None = None,
    # --- pegged to stock and VOL orders only ---
    stockRangeLower:                    float        | None = None,
    stockRangeUpper:                    float        | None = None,
    randomizePrice:                     bool         | None = None,
    randomizeSize:                      bool         | None = None,
    # --- volatility orders only ---
    volatility:                         float        | None = None,
    volatilityType:                     int          | None = None,
    deltaNeutralOrderType:              str          | None = None,
    deltaNeutralAuxPrice:               float        | None = None,
    deltaNeutralConId:                  int          | None = None,
    deltaNeutralSettlingFirm:           str          | None = None,
    deltaNeutralClearingAccount:        str          | None = None,
    deltaNeutralClearingIntent:         str          | None = None,
    deltaNeutralOpenClose:              str          | None = None,
    deltaNeutralShortSale:              bool         | None = None,
    deltaNeutralShortSaleSlot:          int          | None = None,
    deltaNeutralDesignatedLocation:     str          | None = None,
    continuousUpdate:                   bool         | None = None,
    referencePriceType:                 int          | None = None,
    # --- combo orders only ---
    basisPoints:                        float        | None = None,
    basisPointsType:                    int          | None = None,
    # --- scale orders only ---
    scaleInitLevelSize:                 int          | None = None,
    scaleSubsLevelSize:                 int          | None = None,
    scalePriceIncrement:                float        | None = None,
    scalePriceAdjustValue:              float        | None = None,
    scalePriceAdjustInterval:           int          | None = None,
    scaleProfitOffset:                  float        | None = None,
    scaleAutoReset:                     bool         | None = None,
    scaleInitPosition:                  int          | None = None,
    scaleInitFillQty:                   int          | None = None,
    scaleRandomPercent:                 bool         | None = None,
    scaleTable:                         str          | None = None,
    # --- hedge orders ---
    hedgeType:                          str          | None = None,
    hedgeParam:                         str          | None = None,
    # --- clearing ---
    account:                            str          | None = None,
    settlingFirm:                       str          | None = None,
    clearingAccount:                    str          | None = None,
    clearingIntent:                     str          | None = None,
    # --- algo orders only ---
    algoStrategy:                       str          | None = None,
    algoParams:                         list         | None = None,
    smartComboRoutingParams:            list         | None = None,
    algoId:                             str          | None = None,
    # --- what-if / misc ---
    whatIf:                             bool         | None = None,
    notHeld:                            bool         | None = None,
    solicited:                          bool         | None = None,
    modelCode:                          str          | None = None,
    orderComboLegs:                     list         | None = None,
    orderMiscOptions:                   list         | None = None,
    # --- pegged to benchmark ---
    referenceContractId:                int          | None = None,
    peggedChangeAmount:                 float        | None = None,
    isPeggedChangeAmountDecrease:       bool         | None = None,
    referenceChangeAmount:              float        | None = None,
    referenceExchangeId:                str          | None = None,
    adjustedOrderType:                  str          | None = None,
    triggerPrice:                       float        | None = None,
    adjustedStopPrice:                  float        | None = None,
    adjustedStopLimitPrice:             float        | None = None,
    adjustedTrailingAmount:             float        | None = None,
    adjustableTrailingUnit:             int          | None = None,
    lmtPriceOffset:                     float        | None = None,
    # --- conditions ---
    conditions:                         list         | None = None,
    conditionsCancelOrder:              bool         | None = None,
    conditionsIgnoreRth:                bool         | None = None,
    # --- extended misc ---
    extOperator:                        str          | None = None,
    cashQty:                            float        | None = None,
    mifid2DecisionMaker:                str          | None = None,
    mifid2DecisionAlgo:                 str          | None = None,
    mifid2ExecutionTrader:              str          | None = None,
    mifid2ExecutionAlgo:                str          | None = None,
    dontUseAutoPriceForHedge:           bool         | None = None,
    isOmsContainer:                     bool         | None = None,
    discretionaryUpToLimitPrice:        bool         | None = None,
    autoCancelDate:                     str          | None = None,
    refFuturesConId:                    int          | None = None,
    autoCancelParent:                   bool         | None = None,
    shareholder:                        str          | None = None,
    imbalanceOnly:                      bool         | None = None,
    routeMarketableToBbo:               bool         | None = None,
    parentPermId:                       int          | None = None,
    usePriceMgmtAlgo:                   bool         | None = None,
    duration:                           int          | None = None,
    postToAts:                          int          | None = None,
    advancedErrorOverride:              str          | None = None,
    manualOrderTime:                    str          | None = None,
    minTradeQty:                        int          | None = None,
    minCompeteSize:                     int          | None = None,
    competeAgainstBestOffset:           float        | None = None,
    midOffsetAtWhole:                   float        | None = None,
    midOffsetAtHalf:                    float        | None = None,
    customerAccount:                    str          | None = None,
    professionalCustomer:               bool         | None = None,
    bondAccruedInterest:                str          | None = None,
    includeOvernight:                   bool         | None = None,
    manualOrderIndicator:               int          | None = None,
    submitter:                          str          | None = None,
) -> Order:
    """
    General-purpose Order factory. All parameters are optional and
    named exactly as the ibapi Order attributes. Only fields explicitly
    passed are set — everything else is left at the ibapi default.

    Common orderType values
    -----------------------
    LMT     : Limit order — requires lmtPrice
    MKT     : Market order
    STP     : Stop order — requires auxPrice as stop price
    STP LMT : Stop limit — requires lmtPrice and auxPrice
    TRAIL   : Trailing stop — requires trailStopPrice or trailingPercent
    MOC     : Market on close
    LOC     : Limit on close — requires lmtPrice
    MIT     : Market if touched — requires auxPrice
    LIT     : Limit if touched — requires lmtPrice and auxPrice
    REL     : Relative/pegged to primary
    VWAP    : VWAP algorithmic order
    MID     : Midprice order

    Common tif values
    -----------------
    DAY     : expires at end of trading day (default)
    GTC     : good till cancelled
    IOC     : immediate or cancel
    FOK     : fill or kill
    OPG     : at the opening
    MOC     : market on close
    GTD     : good till date — requires goodTillDate

    Example
    -------
    order = make_order(
        action        = \"BUY\",
        orderType     = \"LMT\",
        totalQuantity = Decimal(\"1\"),
        lmtPrice      = 5500.0,
        tif           = \"DAY\",
    )
    """
    o = Order()

    # --- main ---
    if action                            is not None: o.action                            = action
    if totalQuantity                     is not None: o.totalQuantity                     = totalQuantity
    if orderType                         is not None: o.orderType                         = orderType
    if lmtPrice                          is not None: o.lmtPrice                          = lmtPrice
    if auxPrice                          is not None: o.auxPrice                          = auxPrice
    # --- extended ---
    if tif                               is not None: o.tif                               = tif
    if activeStartTime                   is not None: o.activeStartTime                   = activeStartTime
    if activeStopTime                    is not None: o.activeStopTime                    = activeStopTime
    if ocaGroup                          is not None: o.ocaGroup                          = ocaGroup
    if ocaType                           is not None: o.ocaType                           = ocaType
    if orderRef                          is not None: o.orderRef                          = orderRef
    if transmit                          is not None: o.transmit                          = transmit
    if parentId                          is not None: o.parentId                          = parentId
    if blockOrder                        is not None: o.blockOrder                        = blockOrder
    if sweepToFill                       is not None: o.sweepToFill                       = sweepToFill
    if displaySize                       is not None: o.displaySize                       = displaySize
    if triggerMethod                     is not None: o.triggerMethod                     = triggerMethod
    if outsideRth                        is not None: o.outsideRth                        = outsideRth
    if hidden                            is not None: o.hidden                            = hidden
    if goodAfterTime                     is not None: o.goodAfterTime                     = goodAfterTime
    if goodTillDate                      is not None: o.goodTillDate                      = goodTillDate
    if rule80A                           is not None: o.rule80A                           = rule80A
    if allOrNone                         is not None: o.allOrNone                         = allOrNone
    if minQty                            is not None: o.minQty                            = minQty
    if percentOffset                     is not None: o.percentOffset                     = percentOffset
    if overridePercentageConstraints     is not None: o.overridePercentageConstraints     = overridePercentageConstraints
    if trailStopPrice                    is not None: o.trailStopPrice                    = trailStopPrice
    if trailingPercent                   is not None: o.trailingPercent                   = trailingPercent
    # --- financial advisors ---
    if faGroup                           is not None: o.faGroup                           = faGroup
    if faMethod                          is not None: o.faMethod                          = faMethod
    if faPercentage                      is not None: o.faPercentage                      = faPercentage
    # --- institutional ---
    if designatedLocation                is not None: o.designatedLocation                = designatedLocation
    if openClose                         is not None: o.openClose                         = openClose
    if origin                            is not None: o.origin                            = origin
    if shortSaleSlot                     is not None: o.shortSaleSlot                     = shortSaleSlot
    if exemptCode                        is not None: o.exemptCode                        = exemptCode
    # --- SMART routing ---
    if discretionaryAmt                  is not None: o.discretionaryAmt                  = discretionaryAmt
    if optOutSmartRouting                is not None: o.optOutSmartRouting                = optOutSmartRouting
    # --- BOX exchange ---
    if auctionStrategy                   is not None: o.auctionStrategy                   = auctionStrategy
    if startingPrice                     is not None: o.startingPrice                     = startingPrice
    if stockRefPrice                     is not None: o.stockRefPrice                     = stockRefPrice
    if delta                             is not None: o.delta                             = delta
    # --- pegged to stock / VOL ---
    if stockRangeLower                   is not None: o.stockRangeLower                   = stockRangeLower
    if stockRangeUpper                   is not None: o.stockRangeUpper                   = stockRangeUpper
    if randomizePrice                    is not None: o.randomizePrice                    = randomizePrice
    if randomizeSize                     is not None: o.randomizeSize                     = randomizeSize
    # --- volatility ---
    if volatility                        is not None: o.volatility                        = volatility
    if volatilityType                    is not None: o.volatilityType                    = volatilityType
    if deltaNeutralOrderType             is not None: o.deltaNeutralOrderType             = deltaNeutralOrderType
    if deltaNeutralAuxPrice              is not None: o.deltaNeutralAuxPrice              = deltaNeutralAuxPrice
    if deltaNeutralConId                 is not None: o.deltaNeutralConId                 = deltaNeutralConId
    if deltaNeutralSettlingFirm          is not None: o.deltaNeutralSettlingFirm          = deltaNeutralSettlingFirm
    if deltaNeutralClearingAccount       is not None: o.deltaNeutralClearingAccount       = deltaNeutralClearingAccount
    if deltaNeutralClearingIntent        is not None: o.deltaNeutralClearingIntent        = deltaNeutralClearingIntent
    if deltaNeutralOpenClose             is not None: o.deltaNeutralOpenClose             = deltaNeutralOpenClose
    if deltaNeutralShortSale             is not None: o.deltaNeutralShortSale             = deltaNeutralShortSale
    if deltaNeutralShortSaleSlot         is not None: o.deltaNeutralShortSaleSlot         = deltaNeutralShortSaleSlot
    if deltaNeutralDesignatedLocation    is not None: o.deltaNeutralDesignatedLocation    = deltaNeutralDesignatedLocation
    if continuousUpdate                  is not None: o.continuousUpdate                  = continuousUpdate
    if referencePriceType                is not None: o.referencePriceType                = referencePriceType
    # --- combo ---
    if basisPoints                       is not None: o.basisPoints                       = basisPoints
    if basisPointsType                   is not None: o.basisPointsType                   = basisPointsType
    # --- scale ---
    if scaleInitLevelSize                is not None: o.scaleInitLevelSize                = scaleInitLevelSize
    if scaleSubsLevelSize                is not None: o.scaleSubsLevelSize                = scaleSubsLevelSize
    if scalePriceIncrement               is not None: o.scalePriceIncrement               = scalePriceIncrement
    if scalePriceAdjustValue             is not None: o.scalePriceAdjustValue             = scalePriceAdjustValue
    if scalePriceAdjustInterval          is not None: o.scalePriceAdjustInterval          = scalePriceAdjustInterval
    if scaleProfitOffset                 is not None: o.scaleProfitOffset                 = scaleProfitOffset
    if scaleAutoReset                    is not None: o.scaleAutoReset                    = scaleAutoReset
    if scaleInitPosition                 is not None: o.scaleInitPosition                 = scaleInitPosition
    if scaleInitFillQty                  is not None: o.scaleInitFillQty                  = scaleInitFillQty
    if scaleRandomPercent                is not None: o.scaleRandomPercent                = scaleRandomPercent
    if scaleTable                        is not None: o.scaleTable                        = scaleTable
    # --- hedge ---
    if hedgeType                         is not None: o.hedgeType                         = hedgeType
    if hedgeParam                        is not None: o.hedgeParam                        = hedgeParam
    # --- clearing ---
    if account                           is not None: o.account                           = account
    if settlingFirm                      is not None: o.settlingFirm                      = settlingFirm
    if clearingAccount                   is not None: o.clearingAccount                   = clearingAccount
    if clearingIntent                    is not None: o.clearingIntent                    = clearingIntent
    # --- algo ---
    if algoStrategy                      is not None: o.algoStrategy                      = algoStrategy
    if algoParams                        is not None: o.algoParams                        = algoParams
    if smartComboRoutingParams           is not None: o.smartComboRoutingParams           = smartComboRoutingParams
    if algoId                            is not None: o.algoId                            = algoId
    # --- what-if / misc ---
    if whatIf                            is not None: o.whatIf                            = whatIf
    if notHeld                           is not None: o.notHeld                           = notHeld
    if solicited                         is not None: o.solicited                         = solicited
    if modelCode                         is not None: o.modelCode                         = modelCode
    if orderComboLegs                    is not None: o.orderComboLegs                    = orderComboLegs
    if orderMiscOptions                  is not None: o.orderMiscOptions                  = orderMiscOptions
    # --- pegged to benchmark ---
    if referenceContractId               is not None: o.referenceContractId               = referenceContractId
    if peggedChangeAmount                is not None: o.peggedChangeAmount                = peggedChangeAmount
    if isPeggedChangeAmountDecrease      is not None: o.isPeggedChangeAmountDecrease      = isPeggedChangeAmountDecrease
    if referenceChangeAmount             is not None: o.referenceChangeAmount             = referenceChangeAmount
    if referenceExchangeId               is not None: o.referenceExchangeId               = referenceExchangeId
    if adjustedOrderType                 is not None: o.adjustedOrderType                 = adjustedOrderType
    if triggerPrice                      is not None: o.triggerPrice                      = triggerPrice
    if adjustedStopPrice                 is not None: o.adjustedStopPrice                 = adjustedStopPrice
    if adjustedStopLimitPrice            is not None: o.adjustedStopLimitPrice            = adjustedStopLimitPrice
    if adjustedTrailingAmount            is not None: o.adjustedTrailingAmount            = adjustedTrailingAmount
    if adjustableTrailingUnit            is not None: o.adjustableTrailingUnit            = adjustableTrailingUnit
    if lmtPriceOffset                    is not None: o.lmtPriceOffset                    = lmtPriceOffset
    # --- conditions ---
    if conditions                        is not None: o.conditions                        = conditions
    if conditionsCancelOrder             is not None: o.conditionsCancelOrder             = conditionsCancelOrder
    if conditionsIgnoreRth               is not None: o.conditionsIgnoreRth               = conditionsIgnoreRth
    # --- extended misc ---
    if extOperator                       is not None: o.extOperator                       = extOperator
    if cashQty                           is not None: o.cashQty                           = cashQty
    if mifid2DecisionMaker               is not None: o.mifid2DecisionMaker               = mifid2DecisionMaker
    if mifid2DecisionAlgo                is not None: o.mifid2DecisionAlgo                = mifid2DecisionAlgo
    if mifid2ExecutionTrader             is not None: o.mifid2ExecutionTrader             = mifid2ExecutionTrader
    if mifid2ExecutionAlgo               is not None: o.mifid2ExecutionAlgo               = mifid2ExecutionAlgo
    if dontUseAutoPriceForHedge          is not None: o.dontUseAutoPriceForHedge          = dontUseAutoPriceForHedge
    if isOmsContainer                    is not None: o.isOmsContainer                    = isOmsContainer
    if discretionaryUpToLimitPrice       is not None: o.discretionaryUpToLimitPrice       = discretionaryUpToLimitPrice
    if autoCancelDate                    is not None: o.autoCancelDate                    = autoCancelDate
    if refFuturesConId                   is not None: o.refFuturesConId                   = refFuturesConId
    if autoCancelParent                  is not None: o.autoCancelParent                  = autoCancelParent
    if shareholder                       is not None: o.shareholder                       = shareholder
    if imbalanceOnly                     is not None: o.imbalanceOnly                     = imbalanceOnly
    if routeMarketableToBbo              is not None: o.routeMarketableToBbo              = routeMarketableToBbo
    if parentPermId                      is not None: o.parentPermId                      = parentPermId
    if usePriceMgmtAlgo                  is not None: o.usePriceMgmtAlgo                  = usePriceMgmtAlgo
    if duration                          is not None: o.duration                          = duration
    if postToAts                         is not None: o.postToAts                         = postToAts
    if advancedErrorOverride             is not None: o.advancedErrorOverride             = advancedErrorOverride
    if manualOrderTime                   is not None: o.manualOrderTime                   = manualOrderTime
    if minTradeQty                       is not None: o.minTradeQty                       = minTradeQty
    if minCompeteSize                    is not None: o.minCompeteSize                    = minCompeteSize
    if competeAgainstBestOffset          is not None: o.competeAgainstBestOffset          = competeAgainstBestOffset
    if midOffsetAtWhole                  is not None: o.midOffsetAtWhole                  = midOffsetAtWhole
    if midOffsetAtHalf                   is not None: o.midOffsetAtHalf                   = midOffsetAtHalf
    if customerAccount                   is not None: o.customerAccount                   = customerAccount
    if professionalCustomer              is not None: o.professionalCustomer              = professionalCustomer
    if bondAccruedInterest               is not None: o.bondAccruedInterest               = bondAccruedInterest
    if includeOvernight                  is not None: o.includeOvernight                  = includeOvernight
    if manualOrderIndicator              is not None: o.manualOrderIndicator              = manualOrderIndicator
    if submitter                         is not None: o.submitter                         = submitter

    return o


# ---------------------------------------------------------------------------
# make_limit_order — limit order convenience factory
# ---------------------------------------------------------------------------

def make_limit_order(
    *,
    action:              OrderAction | str,
    quantity:            Decimal | int | float,
    price:               float,
    tif:                 TimeInForce | str    = TimeInForce.DAY,
    outsideRth:          bool         | None  = None,
    transmit:            bool         | None  = None,
    orderRef:            str          | None  = None,
    account:             str          | None  = None,
    shortSaleSlot:       int          | None  = None,
    designatedLocation:  str          | None  = None,
    ocaGroup:            str          | None  = None,
    ocaType:             int          | None  = None,
    parentId:            int          | None  = None,
) -> Order:
    """
    Convenience factory for limit orders (orderType='LMT').

    Args:
        action:             OrderAction.BUY or OrderAction.SELL (or raw string).
        quantity:           Number of units to trade.
        price:              Limit price.
        tif:                Time in force. Defaults to DAY.
        outsideRth:         If True, allow execution outside regular trading hours.
        transmit:           If False, order is created in TWS but not sent to exchange.
        orderRef:           Optional free-text order reference tag.
        account:            Optional IB account string (for FA accounts).
        shortSaleSlot:      1 = IB locates shares, 2 = you locate shares.
                            Only needed for institutional / self-locate shorts.
        designatedLocation: Required when shortSaleSlot=2.
        ocaGroup:           One-cancels-all group name.
        ocaType:            OCA type: 1=CANCEL_WITH_BLOCK, 2=REDUCE_WITH_BLOCK,
                            3=REDUCE_NON_BLOCK.
        parentId:           Parent order ID for bracket/attached orders.

    Example:
        order = make_limit_order(
            action   = OrderAction.BUY,
            quantity = 1,
            price    = 5500.0,
        )
        order_id = app.place_order(contract=resolved, order=order)
    """
    action_val = action.value if isinstance(action, OrderAction) else action
    tif_val    = tif.value    if isinstance(tif,    TimeInForce) else tif

    return make_order(
        action             = action_val,
        totalQuantity      = Decimal(str(quantity)),
        orderType          = "LMT",
        lmtPrice           = price,
        tif                = tif_val,
        outsideRth         = outsideRth,
        transmit           = transmit,
        orderRef           = orderRef,
        account            = account,
        shortSaleSlot      = shortSaleSlot,
        designatedLocation = designatedLocation,
        ocaGroup           = ocaGroup,
        ocaType            = ocaType,
        parentId           = parentId,
    )


# ---------------------------------------------------------------------------
# make_market_order — market order convenience factory
# ---------------------------------------------------------------------------

def make_market_order(
    *,
    action:              OrderAction | str,
    quantity:            Decimal | int | float,
    tif:                 TimeInForce | str    = TimeInForce.DAY,
    outsideRth:          bool         | None  = None,
    transmit:            bool         | None  = None,
    orderRef:            str          | None  = None,
    account:             str          | None  = None,
    shortSaleSlot:       int          | None  = None,
    designatedLocation:  str          | None  = None,
    ocaGroup:            str          | None  = None,
    ocaType:             int          | None  = None,
    parentId:            int          | None  = None,
) -> Order:
    """
    Convenience factory for market orders (orderType='MKT').

    Args:
        action:             OrderAction.BUY or OrderAction.SELL (or raw string).
        quantity:           Number of units to trade.
        tif:                Time in force. Defaults to DAY.
        outsideRth:         If True, allow execution outside regular trading hours.
        transmit:           If False, order is created in TWS but not sent to exchange.
        orderRef:           Optional free-text order reference tag.
        account:            Optional IB account string (for FA accounts).
        shortSaleSlot:      1 = IB locates shares, 2 = you locate shares.
        designatedLocation: Required when shortSaleSlot=2.
        ocaGroup:           One-cancels-all group name.
        ocaType:            OCA type: 1=CANCEL_WITH_BLOCK, 2=REDUCE_WITH_BLOCK,
                            3=REDUCE_NON_BLOCK.
        parentId:           Parent order ID for bracket/attached orders.

    Example:
        order = make_market_order(
            action   = OrderAction.BUY,
            quantity = 1,
        )
        order_id = app.place_order(contract=resolved, order=order)
    """
    action_val = action.value if isinstance(action, OrderAction) else action
    tif_val    = tif.value    if isinstance(tif,    TimeInForce) else tif

    return make_order(
        action             = action_val,
        totalQuantity      = Decimal(str(quantity)),
        orderType          = "MKT",
        tif                = tif_val,
        outsideRth         = outsideRth,
        transmit           = transmit,
        orderRef           = orderRef,
        account            = account,
        shortSaleSlot      = shortSaleSlot,
        designatedLocation = designatedLocation,
        ocaGroup           = ocaGroup,
        ocaType            = ocaType,
        parentId           = parentId,
    )