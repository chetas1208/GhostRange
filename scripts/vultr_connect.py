"""Shared SSH connect for ghostrange-control using GHOSTRANGE_CONTROL_SSH_KEY from .env."""

from __future__ import annotations

from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    dotenv = ROOT / ".env"
    if not dotenv.exists():
        raise SystemExit("Missing .env")
    for line in dotenv.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env


def connect(env: dict[str, str] | None = None, *, timeout: float = 30) -> paramiko.SSHClient:
    env = env or load_env()
    host = env["GHOSTRANGE_CONTROL_HOST"]
    user = env.get("GHOSTRANGE_CONTROL_SSH_USER", "root")
    key_path = env.get("GHOSTRANGE_CONTROL_SSH_KEY", str(ROOT / "vultr"))
    passphrase = env.get("GHOSTRANGE_CONTROL_SSH_KEY_PASSPHRASE") or None

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    password = env.get("GHOSTRANGE_CONTROL_SSH_PASSWORD")
    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(key_path, password=passphrase or None)
        client.connect(
            host,
            username=user,
            pkey=pkey,
            timeout=timeout,
            allow_agent=True,
            look_for_keys=False,
        )
        return client
    except paramiko.ssh_exception.PasswordRequiredException:
        if not password:
            raise SystemExit(
                f"SSH key {key_path} is encrypted. Run: ssh-add {key_path}\n"
                "Or set GHOSTRANGE_CONTROL_SSH_KEY_PASSPHRASE in .env"
            ) from None
        client.connect(
            host,
            username=user,
            password=password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        return client


def ssh_argv(env: dict[str, str] | None = None) -> list[str]:
    """OpenSSH argv prefix for rsync/scp (interactive; uses ssh-agent if key encrypted)."""
    env = env or load_env()
    key_path = env.get("GHOSTRANGE_CONTROL_SSH_KEY", str(ROOT / "vultr"))
    return [
        "ssh",
        "-i",
        key_path,
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
