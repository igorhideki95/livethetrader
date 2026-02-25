from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from livethetrader.ui.models import DashboardSnapshot, build_snapshot


@dataclass(slots=True)
class DashboardClient:
    base_url: str = "http://localhost:8000"
    timeout: float = 5.0

    def get_snapshot(self) -> DashboardSnapshot:
        payload = self._request_json("GET", "/api/v1/dashboard")
        return build_snapshot(payload)

    def send_control(self, action: str) -> tuple[bool, str]:
        endpoint = f"/api/v1/dashboard/control/{action}"
        try:
            payload = self._request_json("POST", endpoint)
        except RuntimeError as exc:
            return False, str(exc)

        message = str(payload.get("message") or "comando enviado")
        ok = bool(payload.get("ok", True))
        return ok, message

    def _request_json(self, method: str, path: str) -> dict[str, Any]:
        req = request.Request(
            url=f"{self.base_url.rstrip('/')}{path}",
            method=method,
            headers={"Accept": "application/json"},
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                content = response.read().decode("utf-8")
        except error.URLError as exc:
            raise RuntimeError(f"Falha ao conectar no backend: {exc}") from exc

        if not content:
            return {}

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Resposta inválida do backend (JSON esperado).") from exc

        if not isinstance(data, dict):
            raise RuntimeError("Resposta inválida do backend (objeto JSON esperado).")
        return data
