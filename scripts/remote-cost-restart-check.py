#!/usr/bin/env python3
"""On production: M2 run -> record cost -> restart API -> assert cost persisted."""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


class RedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return urllib.request.Request(newurl, data=req.data, method=req.get_method())


def http_json(method: str, url: str, data: bytes | None = None) -> dict:
    opener = urllib.request.build_opener(RedirectHandler)
    req = urllib.request.Request(url, data=data, method=method)
    with opener.open(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    import paramiko

    env = load_env()
    base = "http://45-76-248-45.nip.io"
    camp = http_json("POST", f"{base}/v1/campaigns/golden")
    rid = camp["range_id"]
    http_json("POST", f"{base}/v1/ranges/{rid}/runs/m2")
    time.sleep(3)
    before = http_json("GET", f"{base}/v1/ranges/{rid}/cost")
    micros = int(before.get("total_known_usd_micros") or 0)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        env["GHOSTRANGE_CONTROL_HOST"],
        username=env.get("GHOSTRANGE_CONTROL_SSH_USER", "root"),
        password=env["GHOSTRANGE_CONTROL_SSH_PASSWORD"],
        timeout=30,
    )
    _stdin, stdout, stderr = client.exec_command(
        "cd /opt/ghostrange && docker compose -f docker-compose.prod.yml restart api && sleep 12"
    )
    stdout.channel.recv_exit_status()
    client.close()

    after = http_json("GET", f"{base}/v1/ranges/{rid}/cost")
    after_micros = int(after.get("total_known_usd_micros") or 0)
    print(json.dumps({"range_id": rid, "before": micros, "after": after_micros, "match": before == after}, indent=2))
    return 0 if before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
