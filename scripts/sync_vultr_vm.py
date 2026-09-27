#!/usr/bin/env python3
"""Upload a filtered tarball to /opt/ghostrange on ghostrange-control."""

from __future__ import annotations

import hashlib
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))
from vultr_connect import connect as ssh_connect
SKIP_TOP = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", "tests/fixtures"}


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    dotenv = ROOT / ".env"
    if not dotenv.exists():
        raise SystemExit("Missing .env with GHOSTRANGE_CONTROL_* SSH settings")
    for line in dotenv.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if rel.parts and rel.parts[0] in SKIP_TOP:
        return True
    if any(".egg-info" in part for part in rel.parts):
        return True
    return path.name in {".env", ".env.production"}


def main() -> None:
    env = load_env()
    with tempfile.NamedTemporaryFile(suffix=".tgz", delete=False) as tmp:
        tpath = tmp.name
    with tarfile.open(tpath, "w:gz") as tar:
        for path in ROOT.rglob("*"):
            if should_skip(path) or not path.is_file():
                continue
            tar.add(path, arcname="ghostrange/" + str(path.relative_to(ROOT)))
    data = Path(tpath).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    print(f"upload size={len(data)} sha256={digest}")

    client = ssh_connect(env, timeout=30)
    sftp = client.open_sftp()
    with sftp.file("/opt/ghostrange-src.tgz", "wb") as remote:
        remote.set_pipelined(True)
        remote.write(data)
    sftp.close()

    cmd = (
        "sha256sum /opt/ghostrange-src.tgz && "
        "test -f /opt/ghostrange/.env.production && cp /opt/ghostrange/.env.production /tmp/ghostrange.env.production.bak || true && "
        "rm -rf /opt/ghostrange && mkdir -p /opt/ghostrange && "
        "tar xzf /opt/ghostrange-src.tgz -C /opt/ghostrange --strip-components=1 && "
        "test -f /tmp/ghostrange.env.production.bak && mv /tmp/ghostrange.env.production.bak /opt/ghostrange/.env.production && chmod 600 /opt/ghostrange/.env.production || true && "
        "rm /opt/ghostrange-src.tgz && test -f /opt/ghostrange/docker-compose.prod.yml && echo SYNC_OK"
    )
    _stdin, stdout, _stderr = client.exec_command(cmd, timeout=300)
    print(stdout.read().decode())
    code = stdout.channel.recv_exit_status()
    client.close()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
