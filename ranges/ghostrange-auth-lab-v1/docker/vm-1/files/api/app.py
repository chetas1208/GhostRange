#!/usr/bin/env python3
"""ghostrange-auth-lab-v1 api tier (api01) — stdlib-only placeholder.

Proves the gateway -> api -> auth chain actually works end to end on real
provisioned infrastructure. This is intentionally minimal: the wave-2 "controlled
scenario" owner replaces this with the real auth-lab application logic (and its
deliberately injected vulnerabilities); the provisioning pipeline (rangespec.yaml,
topology.yaml, docker-compose.yml, cloud-init) does not change when that happens --
only this file's contents (or the image it's baked into) would.

No third-party dependencies: only the Python standard library, so this runs on a
bare `python:3.12-slim` image with no pip install step at boot.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AUTH_URL = os.environ.get("AUTH_URL", "http://auth:8090/verify")


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server's naming convention)
        if self.path == "/health":
            self._send_json(200, {"service": "api", "status": "ok"})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/login":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"

        req = urllib.request.Request(
            AUTH_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                self._send_json(resp.status, json.loads(resp.read() or b"{}"))
        except urllib.error.HTTPError as e:
            self._send_json(e.code, {"error": "auth_service_error", "detail": e.reason})
        except urllib.error.URLError as e:
            self._send_json(502, {"error": "auth_service_unreachable", "detail": str(e.reason)})

    def log_message(self, fmt: str, *args) -> None:  # keep container logs quiet-ish
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()
