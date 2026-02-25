from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaselineThresholds:
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float


DOD_BASELINE_MINIMUM = BaselineThresholds(
    win_rate=0.52,
    profit_factor=1.2,
    expectancy=0.0,
    max_drawdown=-0.02,
)


class DeploymentBlockedError(RuntimeError):
    pass


class StrategyDeploymentGate:
    def __init__(self, baseline: BaselineThresholds = DOD_BASELINE_MINIMUM) -> None:
        self.baseline = baseline

    def validate(self, report: dict) -> None:
        missing = [
            key
            for key in ("win_rate", "profit_factor", "expectancy", "max_drawdown")
            if key not in report
        ]
        if missing:
            raise DeploymentBlockedError(f"Missing backtest metrics required by DoD: {missing}")

        failures: list[str] = []
        if report["win_rate"] < self.baseline.win_rate:
            failures.append(f"win_rate<{self.baseline.win_rate}")
        if report["profit_factor"] < self.baseline.profit_factor:
            failures.append(f"profit_factor<{self.baseline.profit_factor}")
        if report["expectancy"] < self.baseline.expectancy:
            failures.append(f"expectancy<{self.baseline.expectancy}")
        if report["max_drawdown"] < self.baseline.max_drawdown:
            failures.append(f"max_drawdown<{self.baseline.max_drawdown}")

        if failures:
            raise DeploymentBlockedError(
                "Strategy deploy blocked by DoD baseline minimum: " + ", ".join(failures)
            )
