import json

from livethetrader.ml import (
    MLPipeline,
    SignalPublicationGate,
    ThresholdPolicy,
    build_supervised_dataset,
)
from livethetrader.ml.train_cli import run_training


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
        features={"ema_9": 1.3, "ema_21": 0.8},
    )
    assert direction == "CALL"
    assert confidence >= 0.7
    assert "ml_confidence_pass" in reasons

    direction, confidence, reasons = gate.approve(
        strategy_direction="CALL",
        risk_direction="CALL",
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


def test_run_training_cli_flow_generates_versioned_artifact(tmp_path):
    dataset_path = tmp_path / "dataset.jsonl"
    rows = [_sample_row(i) for i in range(18)]
    dataset_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    artifact_path = run_training(
        dataset_path=dataset_path,
        artifact_dir=tmp_path / "artifacts",
        artifact_prefix="signal-gate",
        version_tag="dev",
    )

    assert artifact_path.exists()
    assert artifact_path.name.startswith("signal-gate-dev-")


def test_e2e_train_save_load_and_gate_threshold_decision(tmp_path):
    rows: list[dict] = []
    for i in range(24):
        is_hit = i % 2 == 0
        entry = 1.10 + i * 0.0001
        rows.append(
            {
                "timestamp": f"2025-01-01T00:{i:02d}:00Z",
                "direction": "CALL",
                "base_features": {
                    "ema_9": 1.30 if is_hit else 0.90,
                    "ema_21": 1.00 if is_hit else 1.20,
                    "atr_14": 0.001 if is_hit else 0.0001,
                    "macd_hist": 0.0004 if is_hit else -0.0004,
                    "rsi_14": 60 if is_hit else 40,
                },
                "entry_close": entry,
                "future_close": entry + 0.001 if is_hit else entry - 0.001,
            }
        )

    samples = build_supervised_dataset(rows, lambda row: MLPipeline.build_sample(**row))
    pipeline = MLPipeline(threshold_policy=ThresholdPolicy(minimum_probability=0.58))
    dataset = pipeline.temporal_split(samples)
    pipeline.train(dataset)

    artifact_path = tmp_path / "e2e_ml_artifact.json"
    pipeline.save_artifact(artifact_path)

    loaded_pipeline = MLPipeline(threshold_policy=ThresholdPolicy(minimum_probability=0.58))
    assert loaded_pipeline.load_artifact(artifact_path) is True

    approve_features = next(sample.features for sample in samples if sample.target_hit == 1)
    reject_features = {
        "ema_9": -1.0,
        "ema_21": 2.0,
        "atr_14": 0.0,
        "macd_hist": -0.002,
        "rsi_14": 0.0,
        "return_horizon": -0.01,
        "volatility_context": 0.0,
        "regime_context": -3.0,
    }

    approve_score = loaded_pipeline.predict_probability(approve_features)
    reject_score = loaded_pipeline.predict_probability(reject_features)
    assert approve_score != reject_score

    passing_features = approve_features if approve_score > reject_score else reject_features
    blocking_features = reject_features if approve_score > reject_score else approve_features
    passing_score = max(approve_score, reject_score)
    blocking_score = min(approve_score, reject_score)

    threshold = (passing_score + blocking_score) / 2
    loaded_pipeline.threshold_policy.minimum_probability = threshold

    gate = SignalPublicationGate(ml_pipeline=loaded_pipeline)
    approve_direction, approve_confidence, approve_reasons = gate.approve(
        strategy_direction="CALL",
        risk_direction="CALL",
        features=passing_features,
    )
    reject_direction, reject_confidence, reject_reasons = gate.approve(
        strategy_direction="CALL",
        risk_direction="CALL",
        features=blocking_features,
    )

    assert approve_direction == "CALL"
    assert approve_confidence >= threshold
    assert "ml_confidence_pass" in approve_reasons

    assert reject_direction == "NEUTRO"
    assert reject_confidence < threshold
    assert "ml_confidence_block" in reject_reasons
