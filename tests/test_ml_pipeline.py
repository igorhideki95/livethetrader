from livethetrader.ml import MLPipeline, SignalPublicationGate, build_supervised_dataset


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
    probability = pipeline.predict_probability(dataset.test[0].features)
    assert 0.0 <= probability <= 1.0


def test_signal_publication_gate_requires_strategy_risk_and_ml_confidence():
    gate = SignalPublicationGate()
    features = {
        "ema_9": 1.2,
        "ema_21": 1.0,
        "atr_14": 0.001,
        "macd_hist": 0.001,
        "rsi_14": 55,
    }

    direction, _, reasons = gate.approve(
        strategy_direction="NEUTRO",
        risk_direction="NEUTRO",
        confidence=0.7,
        features=features,
    )
    assert direction == "NEUTRO"
    assert "strategy_rules_block" in reasons

    direction, confidence, reasons = gate.approve(
        strategy_direction="CALL",
        risk_direction="CALL",
        confidence=0.8,
        features=features,
    )
    assert direction in {"CALL", "NEUTRO"}
    assert 0.0 <= confidence <= 1.0
    assert "strategy_rules_pass" in reasons
    assert "risk_guard_pass" in reasons
