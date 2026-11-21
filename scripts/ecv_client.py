"""Tiny HTTP helper shared by the demo scripts. Standard library only (nothing to install)."""
import json
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8000/api"


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"HTTP {status} {code}: {message}")
        self.status, self.code, self.message = status, code, message


def call(base, method, path, body=None, token=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as exc:
        try:
            err = json.loads(exc.read().decode())["error"]
            raise ApiError(exc.code, err.get("code"), err.get("message")) from None
        except (ValueError, KeyError, TypeError):
            raise ApiError(exc.code, "HTTP_ERROR", exc.reason) from None
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot reach the backend at {base} ({exc.reason}). Is it running?") from None


def login(base, username, password):
    return call(base, "POST", "/auth/login", {"username": username, "password": password})["access_token"]