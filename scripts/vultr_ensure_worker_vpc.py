#!/usr/bin/env python3
"""Resolve or create worker VPC in VULTR_WORKER_REGION; update env files.

Run locally: executes on ghostrange-control (Vultr API ACL) via SSH.
Run on VM:    python3 scripts/vultr_ensure_worker_vpc.py --on-host
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def set_env_key(path: Path, key: str, value: str) -> None:
    lines = path.read_text().splitlines() if path.exists() else []
    out: list[str] = []
    found = False
    pat = re.compile(rf"^{re.escape(key)}=")
    for line in lines:
        if pat.match(line):
            out.append(f"{key}={value}")
            found = True
        elif line.strip() == f"# {key}=" or line.strip().startswith(f"# {key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out).rstrip() + "\n")


def vultr_request(api_key: str, method: str, path: str, body: dict | None = None) -> dict:
    url = f"https://api.vultr.com/v2{path}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"Vultr {method} {path} [{exc.code}]: {detail}") from exc


def ensure_vpc(api_key: str, region: str) -> str:
    listed = vultr_request(api_key, "GET", "/vpcs")
    if "error" in listed and "Unauthorized IP" in str(listed.get("error", "")):
        raise RuntimeError(
            "Vultr API IP ACL must include this host's public IP (control VM: 45.76.248.45/32)."
        )
    for vpc in listed.get("vpcs", []):
        if vpc.get("region") == region:
            return vpc["id"]
    created = vultr_request(
        api_key,
        "POST",
        "/vpcs",
        {
            "region": region,
            "description": "ghostrange-worker-vpc",
            "v4_subnet": "10.99.0.0",
            "v4_subnet_mask": 16,
        },
    )
    vpc_id = created.get("vpc", {}).get("id")
    if not vpc_id:
        raise RuntimeError(f"VPC create failed: {created}")
    return vpc_id


def run_on_host(env: dict[str, str]) -> str:
    api_key = env.get("VULTR_API_KEY", "")
    if not api_key:
        raise SystemExit("VULTR_API_KEY missing")
    region = env.get("VULTR_WORKER_REGION", "lax")
    return ensure_vpc(api_key, region)


def sync_vpc_id(vpc_id: str, env: dict[str, str]) -> None:
    if not re.match(r"^[0-9a-f-]{36}$", vpc_id):
        raise SystemExit(f"Invalid VPC id: {vpc_id!r}")
    prod = ROOT / ".env.production"
    local = ROOT / ".env"
    set_env_key(prod, "GHOSTRANGE_WORKER_VPC_ID", vpc_id)
    set_env_key(local, "GHOSTRANGE_WORKER_VPC_ID", vpc_id)
    if local.exists():
        local.chmod(0o600)
    prod.chmod(0o600)

    sys.path.insert(0, str(ROOT / "scripts"))
    from vultr_connect import connect

    patch = (
        f"cd /opt/ghostrange && "
        f"grep -q '^GHOSTRANGE_WORKER_VPC_ID=' .env.production && "
        f"sed -i 's|^GHOSTRANGE_WORKER_VPC_ID=.*|GHOSTRANGE_WORKER_VPC_ID={vpc_id}|' .env.production || "
        f"echo 'GHOSTRANGE_WORKER_VPC_ID={vpc_id}' >> .env.production && "
        f"docker compose -f docker-compose.prod.yml up -d api --force-recreate"
    )
    client = connect(env)
    _stdin, stdout, stderr = client.exec_command(patch, timeout=300)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(err, file=sys.stderr)
    client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--on-host", action="store_true", help="Run Vultr API from this machine (must be ACL-allowed)")
    parser.add_argument(
        "--sync-id",
        metavar="UUID",
        help="Skip API; set GHOSTRANGE_WORKER_VPC_ID locally + on ghostrange-control (from Vultr console)",
    )
    args = parser.parse_args()

    prod = ROOT / ".env.production"
    local = ROOT / ".env"
    env = {**load_env(local), **load_env(prod)}

    if args.sync_id:
        sync_vpc_id(args.sync_id.strip(), env)
        print(args.sync_id.strip())
        return

    if args.on_host:
        vpc_id = run_on_host(env)
    else:
        sys.path.insert(0, str(ROOT / "scripts"))
        from vultr_connect import connect

        client = connect(env)
        sftp = client.open_sftp()
        try:
            sftp.stat("/opt/ghostrange/scripts")
        except FileNotFoundError:
            client.exec_command("mkdir -p /opt/ghostrange/scripts")[1].read()
        local_script = ROOT / "scripts" / "vultr_ensure_worker_vpc.py"
        sftp.put(str(local_script), "/opt/ghostrange/scripts/vultr_ensure_worker_vpc.py")
        sftp.close()

        region = env.get("VULTR_WORKER_REGION", "lax")
        remote = (
            f"cd /opt/ghostrange && set -a && source .env.production && set +a && "
            f"VULTR_WORKER_REGION={region} python3 scripts/vultr_ensure_worker_vpc.py --on-host"
        )
        _stdin, stdout, stderr = client.exec_command(remote, timeout=120)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        code = stdout.channel.recv_exit_status()
        if code != 0:
            raise SystemExit(err or out or f"remote exit {code}")
        # last line should be vpc uuid
        vpc_id = out.splitlines()[-1].strip()
        if not re.match(r"^[0-9a-f-]{36}$", vpc_id):
            raise SystemExit(f"Unexpected remote output:\n{out}")

    set_env_key(prod, "GHOSTRANGE_WORKER_VPC_ID", vpc_id)
    set_env_key(local, "GHOSTRANGE_WORKER_VPC_ID", vpc_id)
    if local.exists():
        local.chmod(0o600)
    prod.chmod(0o600)
    print(vpc_id)

    if not args.on_host:
        # Patch VM production env and recycle API so dry-check picks it up
        sys.path.insert(0, str(ROOT / "scripts"))
        from vultr_connect import connect

        patch = (
            f"cd /opt/ghostrange && "
            f"grep -q '^GHOSTRANGE_WORKER_VPC_ID=' .env.production && "
            f"sed -i 's|^GHOSTRANGE_WORKER_VPC_ID=.*|GHOSTRANGE_WORKER_VPC_ID={vpc_id}|' .env.production || "
            f"echo 'GHOSTRANGE_WORKER_VPC_ID={vpc_id}' >> .env.production && "
            f"docker compose -f docker-compose.prod.yml up -d api --force-recreate"
        )
        client = connect(env)
        _stdin, stdout, stderr = client.exec_command(patch, timeout=300)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(err, file=sys.stderr)


if __name__ == "__main__":
    main()
