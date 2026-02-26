from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from livethetrader.logging import get_logger, log_event
from livethetrader.models import SCHEMA_VERSION, Candle, to_utc_iso

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class TemporalWindow:
    name: str
    start_idx: int
    end_idx: int


class BacktestRunner:
    def __init__(
        self,
        profit_factor_normalization: Literal["none", "null", "cap", "flag"] = "null",
        profit_factor_cap: float = 1_000_000.0,
    ) -> None:
        self.profit_factor_normalization = profit_factor_normalization
        self.profit_factor_cap = profit_factor_cap

    def run(
        self,
        symbol: str,
        candles: list[Candle],
        directions: list[str],
        timeframe: str = "1m",
        strategy_name: str = "mtf_initial_v1",
        report_version: str = "1.0.0",
        report_output_dir: str = "reports",
    ) -> dict:
        if len(candles) < 2:
            raise ValueError("At least two candles are required for backtest")

        log_event(
            LOGGER,
            "backtest_run_started",
            symbol=symbol,
            candles=len(candles),
            directions=len(directions),
            timeframe=timeframe,
            strategy_name=strategy_name,
        )

        default_windows = self.build_temporal_windows(len(candles))
        simulation = self.simulate_temporal_windows(
            candles=candles,
            directions=directions,
            windows=default_windows,
        )
        self._normalize_simulation_profit_factors(simulation)
        aggregate = simulation["aggregate"]

        report = {
            "schema_version": SCHEMA_VERSION,
            "report_version": report_version,
            "report_id": f"bt_{uuid4().hex[:12]}",
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp_open": to_utc_iso(candles[0].timestamp_open),
            "timestamp_close": to_utc_iso(candles[-1].timestamp_close),
            "strategy_name": strategy_name,
            "trades_total": aggregate["trades_total"],
            "win_rate": aggregate["win_rate"],
            "net_pnl": aggregate["net_pnl"],
            "max_drawdown": aggregate["max_drawdown"],
            "sharpe": 0.0,
            "profit_factor": aggregate["profit_factor"],
            "expectancy": aggregate["expectancy"],
            "temporal_windows": simulation["windows"],
            "comparison_by_asset_timeframe": {
                f"{symbol}:{timeframe}": aggregate,
            },
            "comparison_by_market_regime": simulation["comparison_by_market_regime"],
            "generated_at": to_utc_iso(datetime.now(timezone.utc)),
        }
        if "profit_factor_is_infinite" in aggregate:
            report["profit_factor_is_infinite"] = aggregate["profit_factor_is_infinite"]
        report["report_path"] = self.save_report(report, output_dir=report_output_dir)

        log_event(
            LOGGER,
            "backtest_run_completed",
            symbol=symbol,
            report_id=report["report_id"],
            report_path=report["report_path"],
            trades_total=report["trades_total"],
            win_rate=report["win_rate"],
            profit_factor=report["profit_factor"],
        )
        return report

    def build_temporal_windows(self, candle_count: int) -> list[TemporalWindow]:
        if candle_count < 4:
            return [TemporalWindow(name="oos", start_idx=0, end_idx=max(candle_count - 2, 0))]

        tradable = candle_count - 1
        train_end = int(tradable * 0.6)
        valid_end = int(tradable * 0.8)
        return [
            TemporalWindow(name="train", start_idx=0, end_idx=max(train_end - 1, 0)),
            TemporalWindow(
                name="validation", start_idx=train_end, end_idx=max(valid_end - 1, train_end)
            ),
            TemporalWindow(name="oos", start_idx=valid_end, end_idx=tradable - 1),
        ]

    def simulate_temporal_windows(
        self,
        candles: list[Candle],
        directions: list[str],
        windows: list[TemporalWindow],
    ) -> dict:
        window_reports: list[dict] = []
        all_pnl: list[float] = []
        regime_pnl: dict[str, list[float]] = {"bull": [], "bear": [], "sideways": []}

        for window in windows:
            pnl_series: list[float] = []
            wins = 0
            losses = 0
            for idx in range(window.start_idx, window.end_idx + 1):
                if idx >= len(directions) or idx + 1 >= len(candles):
                    continue

                direction = directions[idx]
                if direction == "NEUTRO":
                    continue

                entry = candles[idx].close
                exit_price = candles[idx + 1].close
                delta = exit_price - entry
                pnl = delta if direction == "CALL" else -delta
                pnl_series.append(pnl)
                all_pnl.append(pnl)

                regime = self._market_regime(candles, idx)
                regime_pnl[regime].append(pnl)

                wins += int(pnl > 0)
                losses += int(pnl < 0)

            window_reports.append(
                {
                    "name": window.name,
                    "start": to_utc_iso(candles[window.start_idx].timestamp_open),
                    "end": to_utc_iso(
                        candles[min(window.end_idx + 1, len(candles) - 1)].timestamp_close
                    ),
                    **self._compute_metrics(pnl_series, wins, losses),
                }
            )

        aggregate = self._compute_metrics(
            all_pnl,
            wins=sum(1 for pnl in all_pnl if pnl > 0),
            losses=sum(1 for pnl in all_pnl if pnl < 0),
        )
        comparison_by_market_regime = {
            regime: self._compute_metrics(
                pnl_values,
                wins=sum(1 for pnl in pnl_values if pnl > 0),
                losses=sum(1 for pnl in pnl_values if pnl < 0),
            )
            for regime, pnl_values in regime_pnl.items()
        }

        return {
            "windows": window_reports,
            "aggregate": aggregate,
            "comparison_by_market_regime": comparison_by_market_regime,
        }

    def _normalize_profit_factor(self, profit_factor: float) -> dict:
        is_infinite = profit_factor == float("inf")
        if not is_infinite:
            return {"profit_factor": profit_factor}

        if self.profit_factor_normalization == "null":
            return {"profit_factor": None}
        if self.profit_factor_normalization == "cap":
            return {"profit_factor": round(self.profit_factor_cap, 6)}
        if self.profit_factor_normalization == "flag":
            return {
                "profit_factor": round(self.profit_factor_cap, 6),
                "profit_factor_is_infinite": True,
            }
        return {"profit_factor": profit_factor}

    def _normalize_metrics_profit_factor(self, metrics: dict) -> dict:
        normalized = self._normalize_profit_factor(metrics["profit_factor"])
        metrics["profit_factor"] = normalized["profit_factor"]
        if "profit_factor_is_infinite" in normalized:
            metrics["profit_factor_is_infinite"] = normalized["profit_factor_is_infinite"]
        return metrics

    def _normalize_simulation_profit_factors(self, simulation: dict) -> None:
        for window in simulation["windows"]:
            self._normalize_metrics_profit_factor(window)
        self._normalize_metrics_profit_factor(simulation["aggregate"])
        for metrics in simulation["comparison_by_market_regime"].values():
            self._normalize_metrics_profit_factor(metrics)

    def _market_regime(self, candles: list[Candle], idx: int, lookback: int = 8) -> str:
        if idx < lookback:
            return "sideways"

        past_close = candles[idx - lookback].close
        current_close = candles[idx].close
        pct_change = (current_close - past_close) / max(abs(past_close), 1e-9)

        if pct_change > 0.0015:
            return "bull"
        if pct_change < -0.0015:
            return "bear"
        return "sideways"

    def _compute_metrics(self, pnl_series: list[float], wins: int, losses: int) -> dict:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for pnl in pnl_series:
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
            "trades_total": trades,
            "win_rate": round(win_rate, 4),
            "net_pnl": round(sum(pnl_series), 6),
            "max_drawdown": round(max_drawdown, 6),
            "profit_factor": round(profit_factor, 6)
            if profit_factor != float("inf")
            else float("inf"),
            "expectancy": round(expectancy, 6),
        }

    def save_report(self, report: dict, output_dir: str = "reports") -> str:
        report_dir = Path(output_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = report_dir / f"backtest_{timestamp}_{report['report_id']}.json"
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        return str(path)
