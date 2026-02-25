from __future__ import annotations

from pathlib import Path


def test_ui_app_does_not_depend_on_autorefresh() -> None:
    source = Path("ui/app.py").read_text(encoding="utf-8")

    assert "st.autorefresh" not in source
    assert "st.rerun" in source
