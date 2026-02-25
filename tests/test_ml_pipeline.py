import json

from livethetrader.ml import (
    MLPipeline,
    SignalPublicationGate,
    ThresholdPolicy,
    build_supervised_dataset,
)


def _sample_row(index: int, direction: str = "CALL") -> dict:
    return {
        "timestamp": f"2025-01-01T00:{index:02d}:00Z",
        "direction": direction,
        "base_features": {
            "ema_9": 1.10 + index * 0.001,
            "ema_21": 1.09 + index * 0.001,
            "atr_14": 0.0004 + index * 0.00001,
            "macd_hist": 0.0001,
            "rsi_14": 52,
        },
        "entry_close": 1.10 + index * 0.001,
        "future_close": 1.101 + index * 0.001 if direction == "CALL" else 1.099 + index * 0.001,
    }


def test_build_supervised_target_uses_fixed_horizon_result():
    sample = MLPipeline.build_sample(**_sample_row(1))
    assert sample.target_hit == 1

    losing_call = MLPipeline.build_sample(
        **{**_sample_row(2), "future_close": 1.1005, "entry_close": 1.101}
    )
    assert losing_call.target_hit == 0


def test_temporal_split_and_training_with_probability_calibration():
    pipeline = MLPipeline()
    rows = [_sample_row(i) for i in range(12)]
    samples = build_supervised_dataset(rows, lambda row: MLPipeline.build_sample(**row))

    dataset = pipeline.temporal_split(samples)
    assert len(dataset.train) > 0
    assert len(dataset.validation) > 0

    pipeline.train(dataset)
    assert pipeline.model_ready is True
    probability = pipeline.predict_probability(dataset.test[0].features)
    assert 0.0 <= probability <= 1.0


def test_signal_publication_gate_blocks_when_model_is_not_ready():
    gate = SignalPublicationGate(ml_pipeline=MLPipeline())
    features = {
        "ema_9": 1.2,
        "ema_21": 1.0,
        "atr_14": 0.001,
        "macd_hist": 0.001,
        "rsi_14": 55,
    }

    direction, confidence, reasons = gate.approve(
        strategy_direction="CALL",
        risk_direction="CALL",
        confidence=0.8,
        features=features,
    )
    assert direction == "NEUTRO"
    assert confidence == 0.0
    assert "ml_model_not_ready_block" in reasons


def test_ml_pipeline_load_artifact_and_gate_probability_threshold(tmp_path):
    artifact_path = tmp_path / "model_artifact.json"
    artifact_path.write_text(
        json.dumps(
            {
                "model": {"weights": {"ema_9": 2.0, "ema_21": -1.0}, "bias": 0.0},
                "calibrator": {"a": 1.0, "b": 0.0},
            }
        ),
        encoding="utf-8",
    )

    pipeline = MLPipeline(threshold_policy=ThresholdPolicy(minimum_probability=0.7))
    loaded = pipeline.load_artifact(artifact_path)
    assert loaded is True
    assert pipeline.model_ready is True

    gate = SignalPublicationGate(ml_pipeline=pipeline)
    direction, confidence, reasons = gate.approve(
        strategy_direction="CALL",
        risk_direction="CALL",
        confidence=0.8,
        features={"ema_9": 1.3, "ema_21": 0.8},
    )
    assert direction == "CALL"
    assert confidence >= 0.7
    assert "ml_confidence_pass" in reasons

    direction, confidence, reasons = gate.approve(
        strategy_direction="CALL",
        risk_direction="CALL",
        confidence=0.8,
        features={"ema_9": 0.1, "ema_21": 2.0},
    )
    assert direction == "NEUTRO"
    assert confidence < 0.7
    assert "ml_confidence_block" in reasons


def test_ml_pipeline_missing_artifact_returns_false_and_keeps_fallback_safe(tmp_path):
    pipeline = MLPipeline()

    loaded = pipeline.load_artifact(tmp_path / "missing_model_artifact.json")
    assert loaded is False
    assert pipeline.model_ready is False
    assert pipeline.predict_probability({"ema_9": 1.2, "ema_21": 1.0}) == 0.0
