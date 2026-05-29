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


@mcp.tool()
def get_historical_trades(symbol: str, limit: int = 50, from_id: int = 0) -> str:
    """Get old/historical trades for a symbol.

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        limit: Max trades to return (default 50, max 1000)
        from_id: Trade ID to start from (default: most recent)
    """
    c = _get_client()
    return json.dumps(
        c.get_historical_trades(symbol, limit, from_id or None),
        indent=2, default=str,
    )


def _match_trades(all_trades):
    """Separate fills into entry/exit and match closed trades."""
    from datetime import datetime, timezone
    all_trades.sort(key=lambda t: int(t.get("time", 0)))
    entries, exits = [], []
    for t in all_trades:
        pnl = float(t.get("realizedPnl", t.get("realized_pnl", 0)))
        (exits if pnl != 0.0 else entries).append(t)
    closed = []
    used = set()
    for ex in exits:
        ex_ts = int(ex.get("time", 0))
        best = None
        for i, en in enumerate(entries):
            if i in used:
                continue
            en_ts = int(en.get("time", 0))
            if en_ts < ex_ts and (best is None or en_ts > int(entries[best].get("time", 0))):
                best = i
        if best is not None:
            used.add(best)
            closed.append((entries[best], ex))
        else:
            closed.append((None, ex))
    return closed, len(entries)


@mcp.tool()
def get_user_trades(
    symbol: str = "",
    limit: int = 50,
    start_time: int = 0,
    end_time: int = 0,
) -> str:
    """Get closed trades. Pass symbol for one pair, or omit symbol for ALL closed trades across every pair.

    Args:
        symbol: Trading pair (e.g. GENIUSUSDT). Omit to fetch ALL symbols.
        limit: Max trades per symbol (default 50, max 1000)
        start_time: Start time in epoch ms (optional)
        end_time: End time in epoch ms (optional)
    """
    from datetime import datetime, timezone
    c = _get_client()
    if symbol:
        symbols = [symbol]
    else:
        info = c.get_exchange_info()
        symbols = [s["symbol"] for s in (info if isinstance(info, list) else info.get("symbols", []))]

    all_closed = []
    total_pnl = 0.0
    total_fees = 0.0
    open_count = 0

    for sym in symbols:
        try:
            trades = c.get_user_trades(sym, limit, start_time or None, end_time or None)
        except Exception:
            continue
        if not trades:
            continue
        closed, n_open = _match_trades(trades)
        open_count += n_open
        for entry, exit in closed:
            pnl = float(exit.get("realizedPnl", exit.get("realized_pnl", 0)))
            fee = float(exit.get("commission", 0))
            total_pnl += pnl
            total_fees += fee
            all_closed.append((sym, entry, exit))

    if not all_closed:
        if open_count > 0:
            return f"No closed trades — only {open_count} open position fill(s)."
        return "No trade history found."

    # Sort by exit time
    all_closed.sort(key=lambda x: int(x[2].get("time", 0)))

    lines = [f"Closed Trades — {len(all_closed)} trades\n"]
    for sym, entry, exit in all_closed:
        ex_ts = int(exit.get("time", 0))
        ex_dt = datetime.fromtimestamp(ex_ts / 1000, tz=timezone.utc).strftime("%m/%d %H:%M") if ex_ts else "?"
        ex_price = float(exit.get("price", 0))
        ex_qty = float(exit.get("qty", 0))
        pnl = float(exit.get("realizedPnl", exit.get("realized_pnl", 0)))
        if entry:
            en_ts = int(entry.get("time", 0))
            en_dt = datetime.fromtimestamp(en_ts / 1000, tz=timezone.utc).strftime("%m/%d %H:%M") if en_ts else "?"
            en_price = float(entry.get("price", 0))
            pct = ((ex_price - en_price) / en_price * 100) if en_price else 0
            direction = "LONG" if float(entry.get("qty", 0)) > 0 else "SHORT"
            if direction == "SHORT":
                pct = -pct
            lines.append(f"  {sym}  {en_dt} → {ex_dt}  {direction}  {ex_qty} @ ${en_price:.6g} → ${ex_price:.6g}  ({pct:+.1f}%)  PnL: ${pnl:+.4f}")
        else:
            lines.append(f"  {sym}  ? → {ex_dt}  {ex_qty} @ ${ex_price:.6g}  PnL: ${pnl:+.4f}")
    lines.append(f"\nTotal PnL: ${total_pnl:+.4f}")
    lines.append(f"Total fees: ${total_fees:.6f}")
    if open_count:
        lines.append(f"({open_count} open position fills excluded)")
    return "\n".join(lines)


@mcp.tool()
def get_index_klines(pair: str, interval: str = "1h", limit: int = 100) -> str:
    """Get index price kline/candlestick data.

    Args:
        pair: Trading pair (e.g. BTCUSDT)
        interval: Candle interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w)
        limit: Number of candles (default 100, max 1500)
    """
    c = _get_client()
    return json.dumps(c.get_index_klines(pair, interval, limit), indent=2, default=str)


@mcp.tool()
def get_mark_klines(symbol: str, interval: str = "1h", limit: int = 100) -> str:
    """Get mark price kline/candlestick data.

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        interval: Candle interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w)
        limit: Number of candles (default 100, max 1500)
    """
    c = _get_client()
    return json.dumps(c.get_mark_klines(symbol, interval, limit), indent=2, default=str)


@mcp.tool()
def get_funding_info(symbol: str = "") -> str:
    """Get funding rate configuration (interval hours, cap, floor).

    Args:
        symbol: Trading pair (e.g. BTCUSDT). Omit for all pairs.
    """
    c = _get_client()
    return json.dumps(c.get_funding_info(symbol), indent=2, default=str)


@mcp.tool()
def get_index_references(symbol: str) -> str:
    """Get index price component exchanges and their weights.

    Shows which exchanges (Binance, OKX, Coinbase, etc.) contribute to the index price.

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
    """
    c = _get_client()
    return json.dumps(c.get_index_references(symbol), indent=2, default=str)


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
def get_account_info() -> str:
    """Get full account information with join margin, all assets, and all positions."""
    c = _get_client()
    return json.dumps(c.get_account_info(), indent=2, default=str)


@mcp.tool()
def get_position_margin_history(symbol: str, limit: int = 50) -> str:
    """Get history of margin changes (add/reduce) for a position.

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        limit: Max records to return (default 50)
    """
    c = _get_client()
    return json.dumps(c.get_position_margin_history(symbol, limit), indent=2, default=str)


@mcp.tool()
def modify_order(
    symbol: str,
    order_id: int,
    price: str = "",
    quantity: str = "",
) -> str:
    """Modify an existing LIMIT order without cancel+reorder.

    Only works for LIMIT orders. Both price and quantity must be sent together.

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        order_id: Order ID to modify
        price: New price (optional)
        quantity: New quantity (optional)
    """
    c = _get_client()
    return json.dumps(c.modify_order(symbol, order_id, price, quantity), indent=2, default=str)


@mcp.tool()
def place_chase_order(
    symbol: str,
    side: str,
    quantity: str,
    quantity_unit: str = "BASE",
    time_in_force: str = "GTC",
) -> str:
    """Place a BBO-pegged chase order that auto-tracks the best bid/ask.

    The order automatically re-pegs to best price each tick until filled
    or market moves beyond max offset.

    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        side: BUY or SELL
        quantity: Order quantity
        quantity_unit: BASE or QUOTE (default BASE)
        time_in_force: GTC, IOC, FOK (default GTC, NO_FILL not allowed)
    """
    c = _get_client()
    return json.dumps(c.place_chase_order(symbol, side, quantity, quantity_unit, time_in_force), indent=2, default=str)


@mcp.tool()
def noop() -> str:
    """Cancel in-flight transactions using the same nonce. No guarantee of success."""
    c = _get_client()
    return json.dumps(c.noop(), indent=2, default=str)


# ── STP Mode ─────────────────────────────────────────────────────────

@mcp.tool()
def set_stp_mode(stp_mode: str) -> str:
    """Set Self-Trade Prevention mode on every symbol.

    Args:
        stp_mode: EXPIRE_TAKER, EXPIRE_MAKER, or EXPIRE_BOTH
    """
    c = _get_client()
    return json.dumps(c.set_stp_mode(stp_mode), indent=2, default=str)


@mcp.tool()
def get_stp_mode() -> str:
    """Get current Self-Trade Prevention mode."""
    c = _get_client()
    return json.dumps(c.get_stp_mode(), indent=2, default=str)


# ── Market Maker Protection ──────────────────────────────────────────

@mcp.tool()
def set_mmp(window_ms: int, freeze_ms: int, qty_limit: float, delta_limit: float) -> str:
    """Configure Market Maker Protection.

    Auto-freezes trading when fill limits are exceeded within a time window.

    Args:
        window_ms: Time window in milliseconds
        freeze_ms: Freeze duration in milliseconds after trigger
        qty_limit: Maximum quantity limit within window
        delta_limit: Maximum delta limit within window
    """
    c = _get_client()
    return json.dumps(c.set_mmp(window_ms, freeze_ms, qty_limit, delta_limit), indent=2, default=str)


@mcp.tool()
def get_mmp() -> str:
    """Get current Market Maker Protection configuration."""
    c = _get_client()
    return json.dumps(c.get_mmp(), indent=2, default=str)


@mcp.tool()
def delete_mmp() -> str:
    """Delete Market Maker Protection configuration."""
    c = _get_client()
    return json.dumps(c.delete_mmp(), indent=2, default=str)


@mcp.tool()
def reset_mmp() -> str:
    """Reset/unfreeze Market Maker Protection."""
    c = _get_client()
    return json.dumps(c.reset_mmp(), indent=2, default=str)


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
