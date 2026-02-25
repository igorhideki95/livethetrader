from __future__ import annotations


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    value = sum(values[:period]) / period
    for price in values[period:]:
        value = (price - value) * k + value
    return value


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(abs(min(diff, 0.0)))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    true_ranges: list[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None
    first = sum(true_ranges[:period]) / period
    value = first
    for tr in true_ranges[period:]:
        value = ((value * (period - 1)) + tr) / period
    return value


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, float] | None:
    if len(values) < slow + signal:
        return None
    k_fast = 2 / (fast + 1)
    k_slow = 2 / (slow + 1)

    fast_ema = sum(values[:fast]) / fast
    slow_ema = sum(values[:slow]) / slow
    macd_line_values: list[float] = []

    for idx, price in enumerate(values):
        if idx >= fast:
            fast_ema = (price - fast_ema) * k_fast + fast_ema
        if idx >= slow:
            slow_ema = (price - slow_ema) * k_slow + slow_ema
            macd_line_values.append(fast_ema - slow_ema)

    if len(macd_line_values) < signal:
        return None

    signal_line = sum(macd_line_values[:signal]) / signal
    k_signal = 2 / (signal + 1)
    for value in macd_line_values[signal:]:
        signal_line = (value - signal_line) * k_signal + signal_line

    macd_line = macd_line_values[-1]
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}
