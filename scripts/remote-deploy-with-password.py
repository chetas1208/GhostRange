#!/usr/bin/env python3
"""Deploy to ghostrange-control (pubkey or password from .env)."""
from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k] = v
    return out


def ssh_askpass_env(password: str) -> tuple[dict[str, str], str]:
    fd, path = tempfile.mkstemp(prefix="gr-askpass-")
    os.close(fd)
    script = Path(path)
    script.write_text("#!/bin/sh\nexec printf '%s\\n' \"$SSHPASS_INLINE\"\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    env["SSH_ASKPASS"] = str(script)
    env["SSH_ASKPASS_REQUIRE"] = "force"
    env["SSHPASS_INLINE"] = password
    return env, str(script)


def run_rsync(env_file: dict[str, str], *, use_password: bool) -> int:
    host = env_file["GHOSTRANGE_CONTROL_HOST"]
    user = env_file.get("GHOSTRANGE_CONTROL_SSH_USER", "root")
    key = env_file.get("GHOSTRANGE_CONTROL_SSH_KEY", str(ROOT / "vultr"))
    remote_dir = env_file.get("GHOSTRANGE_REMOTE_DIR", "/opt/ghostrange")
    password = env_file.get("GHOSTRANGE_CONTROL_SSH_PASSWORD", "")

    try:
        sha = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        sha = env_file.get("GHOSTRANGE_DEPLOY_SHA") or "release-evidence-local"
    os.environ["GHOSTRANGE_DEPLOY_SHA"] = sha

    excludes = [
        ".git",
        "node_modules",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".env",
        ".env.production",
        "ranges/**/artifacts",
    ]
    rsync = ["rsync", "-az", "--delete"]
    for ex in excludes:
        rsync.extend(["--exclude", ex])

    dest = f"{user}@{host}:{remote_dir}/"

    if not use_password and Path(key).is_file():
        ssh_e = f"ssh -i {key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
        rsync.extend(["-e", ssh_e, f"{ROOT}/", dest])
        return subprocess.run(rsync).returncode

    if not password:
        print("No SSH key or password available", file=sys.stderr)
        return 1

    env, askpass_path = ssh_askpass_env(password)
    try:
        ssh_e = "ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new"
        rsync.extend(["-e", ssh_e, f"{ROOT}/", dest])
        return subprocess.run(rsync, env=env).returncode
    finally:
        Path(askpass_path).unlink(missing_ok=True)


def run_remote(env_file: dict[str, str], *, use_password: bool) -> int:
    import paramiko

    host = env_file["GHOSTRANGE_CONTROL_HOST"]
    user = env_file.get("GHOSTRANGE_CONTROL_SSH_USER", "root")
    key = env_file.get("GHOSTRANGE_CONTROL_SSH_KEY", str(ROOT / "vultr"))
    password = env_file.get("GHOSTRANGE_CONTROL_SSH_PASSWORD", "")
    remote_dir = env_file.get("GHOSTRANGE_REMOTE_DIR", "/opt/ghostrange")
    sha = os.environ.get("GHOSTRANGE_DEPLOY_SHA", "local")

    remote = f"""set -euo pipefail
cd {remote_dir}
export GHOSTRANGE_DEPLOY_SHA={sha}
bash scripts/deploy-preflight.sh .env.production
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
sleep 14
bash scripts/smoke-test-production.sh http://127.0.0.1
echo DEPLOY_OK
"""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if not use_password and Path(key).is_file():
            client.connect(host, username=user, key_filename=key, timeout=30, allow_agent=False, look_for_keys=False)
        else:
            client.connect(host, username=user, password=password, timeout=30, allow_agent=False, look_for_keys=False)
        _stdin, stdout, stderr = client.exec_command(remote, timeout=3600)
        out = stdout.read().decode()
        err = stderr.read().decode()
        code = stdout.channel.recv_exit_status()
        sys.stdout.write(out)
        sys.stderr.write(err)
        return code
    finally:
        client.close()


def main() -> int:
    env_file = load_env(ROOT / ".env")
    if not env_file.get("GHOSTRANGE_CONTROL_HOST"):
        print("Missing GHOSTRANGE_CONTROL_HOST", file=sys.stderr)
        return 1

    key = env_file.get("GHOSTRANGE_CONTROL_SSH_KEY", str(ROOT / "vultr"))
    use_password = True
    if Path(key).is_file():
        test = subprocess.run(
            ["ssh", "-i", key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", f"root@{env_file['GHOSTRANGE_CONTROL_HOST']}", "echo ok"],
            capture_output=True,
        )
        use_password = test.returncode != 0

    rc = run_rsync(env_file, use_password=use_password)
    if rc != 0:
        return rc
    return run_remote(env_file, use_password=use_password)


if __name__ == "__main__":
    raise SystemExit(main())
