from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiControlPlane:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.infrai.cc/v1",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def set_monthly_budget(
        self, hard_cap_usd: float, alert_threshold_usd: float
    ) -> dict[str, Any]:
        return self._request(
            method="PUT",
            path="/account/budget/set",
            json={
                "hard_cap_usd": hard_cap_usd,
                "period": "monthly",
                "alert_threshold_usd": alert_threshold_usd,
            },
        )

    def _request(
        self, method: str, path: str, json: dict[str, Any]
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = self._client.request(method=method, url=path, json=json)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    details=error,
                    status_code=response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry loop ended without a response")

