"""Aster DEX MCP Server — Phase 1: Core trading tools."""

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import AsterClient
from .ta import analyze_timeframe

mcp = FastMCP("asterdex-mcp")
client: AsterClient | None = None


def _get_client() -> AsterClient:
    global client
    if client is None:
        client = AsterClient()
    return client


# ── Account tools ─────────────────────────────────────────────────────

@mcp.tool()
def get_balance() -> str:
    """Get account balance and margin summary. Returns USDT balance, available margin, and total positions value."""
    c = _get_client()
    return json.dumps(c.get_balance(), indent=2, default=str)


@mcp.tool()
def get_positions() -> str:
    """Get all open positions with entry price, current PnL, leverage, and margin."""
    c = _get_client()
    return json.dumps(c.get_positions(), indent=2, default=str)


@mcp.tool()
def get_open_orders(symbol: str = "") -> str:
    """Get all pending orders. Optionally filter by symbol (e.g. BTCUSDT)."""
    c = _get_client()
    return json.dumps(c.get_open_orders(symbol or None), indent=2, default=str)


# ── Trading tools ─────────────────────────────────────────────────────

@mcp.tool()
def place_order(
    symbol: str,
    side: str,
    type: str,
    quantity: str = "",
    price: str = "",
    stop_price: str = "",
    close_position: bool = False,
    working_type: str = "MARK_PRICE",
    time_in_force: str = "GTC",
    reduce_only: bool = False,
    leverage: int = 0,
) -> str:
    """Place an order on Aster DEX.

    Types: MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET, STOP

    For stop-loss: type=STOP_MARKET, close_position=true, stop_price=SL price
    For take-profit: type=TAKE_PROFIT_MARKET, close_position=true, stop_price=TP price
    For limit: type=LIMIT, price=limit price, quantity=amount
    For market: type=MARKET, quantity=amount

    Args:
        symbol: Trading pair (e.g. TONUSDT)
        side: BUY or SELL
        type: Order type (MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET, STOP)
        quantity: Order quantity (not needed when close_position=true)
        price: Limit price (required for LIMIT orders)
        stop_price: Trigger price (required for STOP_MARKET/TAKE_PROFIT_MARKET)
        close_position: Close entire position (for TP/SL orders)
        working_type: MARK_PRICE or CONTRACT_PRICE
        time_in_force: GTC, IOC, FOK, GTX
        reduce_only: Reduce-only order
        leverage: Set leverage before placing (1-125, optional)
    """
    c = _get_client()
    return json.dumps(c.place_order(
        symbol=symbol,
        side=side,
        type=type,
        quantity=quantity or None,
        price=price or None,
        stop_price=stop_price or None,
        close_position=close_position,
        working_type=working_type,
        time_in_force=time_in_force,
        reduce_only=reduce_only,
        leverage=leverage or None,
    ), indent=2, default=str)


@mcp.tool()
def cancel_order(symbol: str, order_id: int) -> str:
    """Cancel a specific open order by its order ID.

    Args:
        symbol: Trading pair (e.g. TONUSDT)
        order_id: Order ID to cancel
    """
    c = _get_client()
    return json.dumps(c.cancel_order(symbol, order_id), indent=2, default=str)


@mcp.tool()
def cancel_all_orders(symbol: str = "") -> str:
    """Cancel all open orders, optionally filtered by symbol.

    Args:
        symbol: Filter by trading pair. Omit to cancel ALL open orders.
    """
    c = _get_client()
    return json.dumps(c.cancel_all_orders(symbol or None), indent=2, default=str)


# ── TA tools ──────────────────────────────────────────────────────────

@mcp.tool()
def analyze_coin(
    symbol: str,
    intervals: str = "1h,4h,1d",
    limit: int = 200,
) -> str:
    """Full technical analysis for a coin across multiple timeframes.

    Returns RSI, MACD, Stochastic, EMA (9/20/50/200), Bollinger Bands,
    Pivot Points, volume ratio, and a BUY/SELL/HOLD signal for each timeframe.

    Args:
        symbol: Trading pair (e.g. BTCUSDT, TONUSDT)
        intervals: Comma-separated timeframes (e.g. "1h,4h,1d"). Options: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w
        limit: Number of candles per timeframe (default 200, need 50+ for EMA50, 200+ for EMA200)
    """
    c = _get_client()
    symbol = symbol.upper()
    tf_list = [t.strip() for t in intervals.split(",")]

    results = {}
    for tf in tf_list:
        klines = c.get_klines(symbol, tf, limit)
        if not klines or len(klines) < 30:
            results[tf] = {"error": "insufficient data"}
            continue

        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        volumes = [k["volume"] for k in klines]

        results[tf] = analyze_timeframe(closes, highs, lows, volumes)

    return json.dumps(results, indent=2, default=str)


# ── Market data tools ─────────────────────────────────────────────────

@mcp.tool()
def get_klines(symbol: str, interval: str = "1h", limit: int = 100) -> str:
    """Get OHLCV candle data for a trading pair.

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        interval: Candle interval. Options: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w
        limit: Number of candles (max 1500, default 100)
    """
    c = _get_client()
    return json.dumps(c.get_klines(symbol, interval, limit), indent=2, default=str)


@mcp.tool()
def get_ticker(symbol: str = "") -> str:
    """Get 24h price/volume ticker. Omit symbol for all trading pairs.

    Args:
        symbol: Trading pair (e.g. BTCUSDT). Omit for all tickers.
    """
    c = _get_client()
    return json.dumps(c.get_ticker(symbol or None), indent=2, default=str)


@mcp.tool()
def get_orderbook(symbol: str, limit: int = 20) -> str:
    """Get L2 orderbook depth (bids and asks).

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        limit: Depth levels (5, 10, 20, 50, 100, 500. default 20)
    """
    c = _get_client()
    return json.dumps(c.get_orderbook(symbol, limit), indent=2, default=str)


# ── Exchange tools ────────────────────────────────────────────────────

@mcp.tool()
def set_leverage(symbol: str, leverage: int) -> str:
    """Set leverage for a trading pair.

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        leverage: Leverage multiplier (1-125)
    """
    c = _get_client()
    return json.dumps(c.set_leverage(symbol, leverage), indent=2, default=str)


@mcp.tool()
def get_exchange_info(symbol: str = "") -> str:
    """Get exchange info — precision, leverage limits, filters. Omit symbol for all trading pairs.

    Args:
        symbol: Trading pair (e.g. BTCUSDT). Omit for all pairs summary.
    """
    c = _get_client()
    return json.dumps(c.get_exchange_info(symbol or None), indent=2, default=str)


# ── Entry point ───────────────────────────────────────────────────────

def main():
    mcp.run()


if __name__ == "__main__":
    main()
