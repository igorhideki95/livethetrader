from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from livethetrader.models import Candle, SCHEMA_VERSION, to_utc_iso


class BacktestRunner:
    def run(self, symbol: str, candles: list[Candle], directions: list[str]) -> dict:
        if len(candles) < 2:
            raise ValueError("At least two candles are required for backtest")

        pnl_series: list[float] = []
        wins = 0
        losses = 0
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for idx, direction in enumerate(directions):
            if idx + 1 >= len(candles) or direction == "NEUTRO":
                continue
            entry = candles[idx].close
            exit_price = candles[idx + 1].close
            delta = exit_price - entry
            pnl = delta if direction == "CALL" else -delta
            pnl_series.append(pnl)
            wins += int(pnl > 0)
            losses += int(pnl < 0)
            equity += pnl
            peak = max(peak, equity)
            max_drawdown = min(max_drawdown, equity - peak)

        trades = len(pnl_series)
        win_rate = wins / trades if trades else 0.0
        gross_profit = sum(v for v in pnl_series if v > 0)
        gross_loss = abs(sum(v for v in pnl_series if v < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss else float("inf")
        expectancy = (sum(pnl_series) / trades) if trades else 0.0

        return {
            "schema_version": SCHEMA_VERSION,
            "report_id": f"bt_{uuid4().hex[:12]}",
            "symbol": symbol,
            "timeframe": "1m",
            "timestamp_open": to_utc_iso(candles[0].timestamp_open),
            "timestamp_close": to_utc_iso(candles[-1].timestamp_close),
            "strategy_name": "mtf_initial_v1",
            "trades_total": trades,
            "win_rate": round(win_rate, 4),
            "net_pnl": round(sum(pnl_series), 6),
            "max_drawdown": round(max_drawdown, 6),
            "sharpe": 0.0,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "generated_at": to_utc_iso(datetime.now(timezone.utc)),
        }
