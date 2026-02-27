from __future__ import annotations

from io import StringIO

from livethetrader.interface.console import render_snapshot, run_interface
from livethetrader.interface.models import DashboardSnapshot


class _FakeInterfaceService:
    def __init__(self, responses: list[tuple[DashboardSnapshot | None, str | None]]) -> None:
        self._responses = responses
        self._index = 0

    def fetch_snapshot(self) -> tuple[DashboardSnapshot | None, str | None]:
        if self._index >= len(self._responses):
            return self._responses[-1]
        response = self._responses[self._index]
        self._index += 1
        return response


def _build_snapshot() -> DashboardSnapshot:
    payload = {
        "symbol": "EURUSD",
        "timeframe": "1m",
        "last_signal": "CALL",
        "confidence": 0.74,
        "system_status": "ONLINE",
        "metrics": {
            "win_rate": 0.58,
            "profit_factor": 1.4,
            "drawdown": 0.07,
            "trades_total": 55,
        },
        "history": [
            {
                "signal_id": "sig_1",
                "symbol": "EURUSD",
                "timeframe": "1m",
                "direction": "CALL",
                "confidence": 0.74,
                "timestamp_open": "2025-01-01T10:00:00Z",
            }
        ],
    }
    return DashboardSnapshot.from_payload(payload)


def test_render_snapshot_matches_terminal_layout():
    output = render_snapshot(_build_snapshot())

    assert "LiveTheTrader Interface (MVP)" in output
    assert "Ativo: EURUSD" in output
    assert "Confiança: 74.00%" in output
    assert "win_rate: 58.00%" in output
    assert "EURUSD 1m | CALL" in output


def test_run_interface_smoke_renders_dashboard_with_fake_client(monkeypatch):
    recorded_events: list[tuple[str, dict]] = []

    def _fake_log_event(_logger, event: str, **kwargs):
        recorded_events.append((event, kwargs))

    monkeypatch.setattr("livethetrader.interface.console.log_event", _fake_log_event)

    stream = StringIO()
    fake_service = _FakeInterfaceService([(_build_snapshot(), None)])

    run_interface(
        base_url="http://unused",
        interval=0,
        render_terminal=True,
        output_stream=stream,
        sleep_fn=lambda _value: None,
        interface_service=fake_service,
        max_iterations=1,
    )

    output = stream.getvalue()
    assert output.startswith("\033[2J\033[H")
    assert "Ativo: EURUSD" in output
    assert recorded_events[0][0] == "interface_snapshot_received"


def test_run_interface_log_only_skips_terminal_output(monkeypatch):
    recorded_events: list[tuple[str, dict]] = []

    def _fake_log_event(_logger, event: str, **kwargs):
        recorded_events.append((event, kwargs))

    monkeypatch.setattr("livethetrader.interface.console.log_event", _fake_log_event)

    stream = StringIO()
    fake_service = _FakeInterfaceService([(_build_snapshot(), None)])

    run_interface(
        base_url="http://unused",
        interval=0,
        render_terminal=False,
        output_stream=stream,
        sleep_fn=lambda _value: None,
        interface_service=fake_service,
        max_iterations=1,
    )

    assert stream.getvalue() == ""
    assert recorded_events[0][0] == "interface_snapshot_received"
