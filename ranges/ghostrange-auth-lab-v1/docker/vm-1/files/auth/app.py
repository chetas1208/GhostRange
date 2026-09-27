#!/usr/bin/env python3
"""ghostrange-auth-lab-v1 auth tier (auth01) — stdlib-only placeholder.

Checks credentials against an in-memory, obviously-fake demo credential set (this is
a disposable lab range, never a real secret store) and confirms the data store tier
is actually live and reachable over the network on every /verify call, so the full
gateway -> api -> auth -> data-store chain is exercised on every request, not just at
boot.

Deliberately does NOT execute real SQL against the data store yet (that's scenario
content -- e.g. real credential lookups, real audit persistence -- owned by the
wave-2 "controlled scenario" agent). ranges/ghostrange-auth-lab-v1/docker/vm-1/files/
data-store/init.sql already creates the `login_attempts` table this would write to,
so wiring a real DB driver in later is a same-file change, not a re-architecture.

No third-party dependencies: standard library only.
"""

from __future__ import annotations

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Obviously-fake, lab-only demo credentials. Never a real secret.
DEMO_CREDENTIALS = {"demo": "ghostrange-lab-only"}

DATA_STORE_HOST = os.environ.get("DATA_STORE_HOST", "data-store")
DATA_STORE_PORT = int(os.environ.get("DATA_STORE_PORT", "5432"))


def data_store_reachable() -> bool:
    try:
        with socket.create_connection((DATA_STORE_HOST, DATA_STORE_PORT), timeout=2):
            return True
    except OSError:
        return False


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(
                200, {"service": "auth", "status": "ok", "data_store_reachable": data_store_reachable()}
            )
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/verify":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            creds = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        username = creds.get("username", "")
        password = creds.get("password", "")
        authenticated = DEMO_CREDENTIALS.get(username) == password
        reachable = data_store_reachable()

        # Stub audit line -- real durable evidence writes belong to packages/evidence
        # (owned by a different M2 agent), not this placeholder.
        print(
            f"[auth] verify username={username!r} authenticated={authenticated} "
            f"data_store_reachable={reachable}"
        )

        self._send_json(
            200 if authenticated else 401,
            {"authenticated": authenticated, "data_store_reachable": reachable},
        )

    def log_message(self, fmt: str, *args) -> None:
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8090), Handler)
    server.serve_forever()
