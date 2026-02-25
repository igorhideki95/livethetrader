from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable

from livethetrader.models import Direction


@dataclass(slots=True, frozen=True)
class SupervisedSample:
    timestamp: str
    direction: Direction
    features: dict[str, float]
    target_hit: int


@dataclass(slots=True, frozen=True)
class DatasetBundle:
    train: list[SupervisedSample]
    validation: list[SupervisedSample]
    test: list[SupervisedSample]


@dataclass(slots=True)
class ThresholdPolicy:
    minimum_probability: float = 0.58


class LinearProbabilityModel:
    """Fallback probabilistic model used when sklearn is unavailable."""

    def __init__(self) -> None:
        self._weights: dict[str, float] = {}
        self._bias: float = 0.0

    def fit(self, samples: list[SupervisedSample]) -> None:
        if not samples:
            self._weights = {}
            self._bias = 0.0
            return

        features = sorted({name for sample in samples for name in sample.features})
        positives = [sample for sample in samples if sample.target_hit == 1]
        negatives = [sample for sample in samples if sample.target_hit == 0]

        if not positives or not negatives:
            self._weights = {name: 0.0 for name in features}
            self._bias = 0.0
            return

        self._weights = {}
        for name in features:
            pos_mean = mean(sample.features.get(name, 0.0) for sample in positives)
            neg_mean = mean(sample.features.get(name, 0.0) for sample in negatives)
            self._weights[name] = pos_mean - neg_mean

        hit_rate = sum(sample.target_hit for sample in samples) / len(samples)
        hit_rate = min(max(hit_rate, 1e-6), 1 - 1e-6)
        self._bias = math.log(hit_rate / (1 - hit_rate))

    def predict_proba(self, features: dict[str, float]) -> float:
        logit = self._bias
        for name, weight in self._weights.items():
            logit += features.get(name, 0.0) * weight
        return 1.0 / (1.0 + math.exp(-max(min(logit, 30.0), -30.0)))


class PlattCalibrator:
    """Simple Platt scaling trained with gradient descent over probabilities."""

    def __init__(self, learning_rate: float = 0.05, iterations: int = 600) -> None:
        self.learning_rate = learning_rate
        self.iterations = iterations
        self.a = 1.0
        self.b = 0.0

    def fit(self, probabilities: list[float], labels: list[int]) -> None:
        if not probabilities or len(probabilities) != len(labels):
            return

        a, b = self.a, self.b
        for _ in range(self.iterations):
            grad_a = 0.0
            grad_b = 0.0
            for prob, label in zip(probabilities, labels, strict=True):
                x = math.log(min(max(prob, 1e-6), 1 - 1e-6) / (1 - min(max(prob, 1e-6), 1 - 1e-6)))
                pred = 1.0 / (1.0 + math.exp(-(a * x + b)))
                err = pred - label
                grad_a += err * x
                grad_b += err
            a -= self.learning_rate * grad_a / len(probabilities)
            b -= self.learning_rate * grad_b / len(probabilities)

        self.a, self.b = a, b

    def transform(self, probability: float) -> float:
        p = min(max(probability, 1e-6), 1 - 1e-6)
        x = math.log(p / (1 - p))
        return 1.0 / (1.0 + math.exp(-(self.a * x + self.b)))


class MLPipeline:
    """Pipeline for dataset generation, temporal split, training and calibration."""

    def __init__(self, threshold_policy: ThresholdPolicy | None = None) -> None:
        self.threshold_policy = threshold_policy or ThresholdPolicy()
        self.model = LinearProbabilityModel()
        self.calibrator = PlattCalibrator()
        self.model_ready = False

    @staticmethod
    def build_sample(
        *,
        timestamp: str,
        direction: Direction,
        base_features: dict[str, float],
        future_close: float,
        entry_close: float,
    ) -> SupervisedSample:
        returns = (future_close - entry_close) / max(entry_close, 1e-9)
        volatility = abs(base_features.get("atr_14", 0.0)) / max(
            base_features.get("ema_21", 1.0), 1e-9
        )
        regime = base_features.get("ema_9", 0.0) - base_features.get("ema_21", 0.0)

        target_hit = 0
        if direction == "CALL":
            target_hit = int(future_close > entry_close)
        elif direction == "PUT":
            target_hit = int(future_close < entry_close)

        features = dict(base_features)
        features.update(
            {
                "return_horizon": returns,
                "volatility_context": volatility,
                "regime_context": regime,
            }
        )

        return SupervisedSample(
            timestamp=timestamp,
            direction=direction,
            features=features,
            target_hit=target_hit,
        )

    @staticmethod
    def temporal_split(samples: list[SupervisedSample]) -> DatasetBundle:
        ordered = sorted(samples, key=lambda sample: sample.timestamp)
        n = len(ordered)
        train_end = max(1, int(n * 0.6))
        validation_end = max(train_end + 1, int(n * 0.8))

        return DatasetBundle(
            train=ordered[:train_end],
            validation=ordered[train_end:validation_end],
            test=ordered[validation_end:],
        )

    def train(self, dataset: DatasetBundle) -> None:
        if not dataset.train:
            self.model_ready = False
            return
        self.model.fit(dataset.train)
        val_raw = [self.model.predict_proba(sample.features) for sample in dataset.validation]
        labels = [sample.target_hit for sample in dataset.validation]
        self.calibrator.fit(val_raw, labels)
        self.model_ready = True

    def load_artifact(self, artifact_path: str | Path) -> bool:
        path = Path(artifact_path)
        if not path.exists():
            self.model_ready = False
            return False

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self.model_ready = False
            return False

        model_data = payload.get("model", {})
        calibrator_data = payload.get("calibrator", {})

        self.model._weights = {
            str(name): float(weight) for name, weight in model_data.get("weights", {}).items()
        }
        self.model._bias = float(model_data.get("bias", 0.0))
        self.calibrator.a = float(calibrator_data.get("a", 1.0))
        self.calibrator.b = float(calibrator_data.get("b", 0.0))
        self.model_ready = True
        return True

    def predict_probability(self, features: dict[str, float]) -> float:
        if not self.model_ready:
            return 0.0
        raw = self.model.predict_proba(features)
        return self.calibrator.transform(raw)

    def passes_operational_threshold(self, probability: float) -> bool:
        return probability >= self.threshold_policy.minimum_probability


class SignalPublicationGate:
    """Publishes only signals passing strategy, risk and ML confidence gates."""

    def __init__(self, ml_pipeline: MLPipeline | None = None) -> None:
        self.ml_pipeline = ml_pipeline or MLPipeline()

    def approve(
        self,
        *,
        strategy_direction: Direction,
        risk_direction: Direction,
        features: dict[str, float],
    ) -> tuple[Direction, float, list[str]]:
        reasons: list[str] = []
        if strategy_direction == "NEUTRO":
            return "NEUTRO", 0.0, ["strategy_rules_block"]
        reasons.append("strategy_rules_pass")

        if risk_direction == "NEUTRO":
            return "NEUTRO", 0.0, reasons + ["risk_guard_block"]
        reasons.append("risk_guard_pass")

        if not self.ml_pipeline.model_ready:
            return "NEUTRO", 0.0, reasons + ["ml_model_not_ready_block"]

        ml_probability = self.predict_ml_confidence(features)
        if not self.ml_pipeline.passes_operational_threshold(ml_probability):
            return "NEUTRO", ml_probability, reasons + ["ml_confidence_block"]

        return risk_direction, ml_probability, reasons + ["ml_confidence_pass"]

    def predict_ml_confidence(self, features: dict[str, float]) -> float:
        return self.ml_pipeline.predict_probability(features)


def build_supervised_dataset(
    rows: list[dict],
    sample_builder: Callable[[dict], SupervisedSample],
) -> list[SupervisedSample]:
    return [sample_builder(row) for row in rows]
