"""Technical analysis engine — RSI, MACD, Stochastic, EMA, Bollinger Bands."""

import numpy as np
from typing import Any


def ema(data: list[float], period: int) -> list[float]:
    """Exponential Moving Average."""
    k = 2 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(data[i] * k + result[-1] * (1 - k))
    return result


def rsi(closes: list[float], period: int = 14) -> list[float]:
    """Relative Strength Index."""
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    rsis = []
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsis.append(100)
        else:
            rsis.append(100 - 100 / (1 + avg_gain / avg_loss))
    return rsis


def macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float, float, float]:
    """MACD line, signal line, histogram."""
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
    signal_line = ema(macd_line, signal)
    hist = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
    return macd_line[-1], signal_line[-1], hist[-1]


def stochastic(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[float, float]:
    """Stochastic %K and %D."""
    k_values = []
    for i in range(k_period - 1, len(closes)):
        h = max(highs[i - k_period + 1 : i + 1])
        l = min(lows[i - k_period + 1 : i + 1])
        if h == l:
            k_values.append(50)
        else:
            k_values.append((closes[i] - l) / (h - l) * 100)
    d_values = ema(k_values, d_period)
    return k_values[-1], d_values[-1]


def bollinger(
    closes: list[float],
    period: int = 20,
    std_mult: float = 2,
) -> tuple[float | None, float | None, float | None]:
    """Bollinger Bands: upper, mid, lower."""
    if len(closes) < period:
        return None, None, None
    sma = float(np.mean(closes[-period:]))
    std = float(np.std(closes[-period:]))
    return sma + std_mult * std, sma, sma - std_mult * std


def pivot_points(
    highs: list[float],
    lows: list[float],
    closes: list[float],
) -> tuple[float, float, float]:
    """Pivot Point, R1, S1 from previous candle."""
    h1, l1, c1 = highs[-2], lows[-2], closes[-2]
    pivot = (h1 + l1 + c1) / 3
    r1 = 2 * pivot - l1
    s1 = 2 * pivot - h1
    return pivot, r1, s1


def compute_signal(
    rsi_val: float | None,
    stoch_k: float,
    macd_line: float,
    macd_signal: float,
    histogram: float,
    price: float,
    ema20_val: float,
    ema50_val: float | None,
) -> tuple[str, int, int]:
    """Generate BUY/SELL/HOLD signal from indicators."""
    bull = 0
    bear = 0

    if rsi_val is not None:
        if rsi_val < 30:
            bull += 2
        elif rsi_val < 40:
            bull += 1
        elif rsi_val > 70:
            bear += 2
        elif rsi_val > 60:
            bear += 1

    if stoch_k < 20:
        bull += 2
    elif stoch_k < 30:
        bull += 1
    elif stoch_k > 80:
        bear += 2
    elif stoch_k > 70:
        bear += 1

    if histogram > 0 and macd_line > macd_signal:
        bull += 1
    elif histogram < 0 and macd_line < macd_signal:
        bear += 1

    above_ema20 = price > ema20_val
    if above_ema20:
        bull += 1
    else:
        bear += 1

    if ema50_val is not None:
        if price > ema50_val:
            bull += 1
        else:
            bear += 1

    if bull >= 4:
        signal = "BUY"
    elif bear >= 4:
        signal = "SELL"
    else:
        signal = "HOLD"

    return signal, bull, bear


def analyze_timeframe(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
) -> dict[str, Any]:
    """Full TA analysis for a single timeframe."""
    price = closes[-1]

    # RSI
    rsi_vals = rsi(closes)
    rsi_val = round(rsi_vals[-1], 1) if rsi_vals else None

    # MACD
    macd_line, signal_line, histogram = macd(closes)

    # Stochastic
    stoch_k, stoch_d = stochastic(highs, lows, closes)

    # EMAs
    ema9_val = ema(closes, 9)[-1]
    ema20_val = ema(closes, 20)[-1]
    ema50_val = ema(closes, 50)[-1] if len(closes) >= 50 else None
    ema200_val = ema(closes, 200)[-1] if len(closes) >= 200 else None

    # Bollinger Bands
    bb_upper, bb_mid, bb_lower = bollinger(closes)

    # Structure
    if ema50_val is not None and ema200_val is not None:
        golden_cross = ema50_val > ema200_val
        structure = "Golden Cross" if golden_cross else "Death Cross"
    else:
        structure = "N/A"

    # BB position
    if bb_upper is not None and bb_lower is not None and bb_mid is not None:
        bb_width = (bb_upper - bb_lower) / bb_mid
        if price > bb_upper:
            bb_pos = "Above Upper"
        elif price > bb_mid:
            bb_pos = "Upper Half"
        elif price > bb_lower:
            bb_pos = "Lower Half"
        else:
            bb_pos = "Below Lower"
    else:
        bb_pos = "N/A"
        bb_width = 0

    # Pivot points
    pivot, r1, s1 = pivot_points(highs, lows, closes)

    # Volume
    vol_avg = float(np.mean(volumes[-20:]))
    vol_ratio = round(volumes[-1] / vol_avg, 1) if vol_avg > 0 else 0

    # Signal
    signal, bull, bear = compute_signal(
        rsi_val, stoch_k, macd_line, signal_line, histogram,
        price, ema20_val, ema50_val,
    )

    return {
        "price": round(price, 6),
        "rsi": rsi_val,
        "stoch_k": round(stoch_k, 1),
        "stoch_d": round(stoch_d, 1),
        "macd_line": round(macd_line, 6),
        "macd_signal": round(signal_line, 6),
        "macd_hist": round(histogram, 6),
        "ema9": round(ema9_val, 6),
        "ema20": round(ema20_val, 6),
        "ema50": round(ema50_val, 6) if ema50_val else None,
        "ema200": round(ema200_val, 6) if ema200_val else None,
        "bb_upper": round(bb_upper, 6) if bb_upper else None,
        "bb_mid": round(bb_mid, 6) if bb_mid else None,
        "bb_lower": round(bb_lower, 6) if bb_lower else None,
        "bb_pos": bb_pos,
        "bb_width": round(bb_width, 4),
        "structure": structure,
        "pivot": round(pivot, 6),
        "r1": round(r1, 6),
        "s1": round(s1, 6),
        "vol_ratio": vol_ratio,
        "signal": signal,
        "bull_signals": bull,
        "bear_signals": bear,
    }
