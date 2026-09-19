"""Cliente HTTP hacia FastAPI. El JWT vive en la sesión Django, nunca en el browser."""

from typing import Any

import requests
from django.conf import settings

TIMEOUT = 10


class ApiError(Exception):
    def __init__(self, status: int, detail: object = "") -> None:
        super().__init__(str(detail))
        self.status = status
        self.detail = detail


def _request(
    method: str, path: str, token: str | None = None, body: dict[str, Any] | None = None
) -> object:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    res = requests.request(
        method, settings.FASTAPI_URL + path, json=body, headers=headers, timeout=TIMEOUT
    )
    if res.status_code in (401, 403):
        raise ApiError(res.status_code, _detalle(res))
    if res.status_code >= 400:
        raise ApiError(res.status_code, _detalle(res))
    return res.json() if res.text else None


def _detalle(res: requests.Response) -> object:
    try:
        data = res.json()
        return data.get("detail", data) if isinstance(data, dict) else data
    except ValueError:
        return res.text[:200]


def login_api(email: str, password: str) -> dict[str, object]:
    data = _request(
        "POST", "/api/auth/login", body={"email": email, "password": password}
    )
    assert isinstance(data, dict)
    return data


def api_get(path: str, token: str, params: dict[str, str] | None = None) -> object:
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(
        settings.FASTAPI_URL + path,
        headers=headers,
        params=params or {},
        timeout=TIMEOUT,
    )
    if res.status_code in (401, 403):
        raise ApiError(res.status_code, _detalle(res))
    if res.status_code >= 400:
        raise ApiError(res.status_code, _detalle(res))
    return res.json() if res.text else None


def api_post(path: str, token: str, body: dict[str, Any]) -> object:
    return _request("POST", path, token=token, body=body)
