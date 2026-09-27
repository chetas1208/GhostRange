"""Vultr user-data for GhostRange worker bootstrap."""


def worker_cloud_init(
    *,
    control_url: str,
    bootstrap_token: str,
    netbird_setup_key: str | None = None,
    netbird_peer_hostname: str | None = None,
) -> str:
    """Minimal cloud-config: Python3 + ghostrange-worker via pip module fetch.

    NetBird mesh enrollment (optional)
    -----------------------------------
    When ``netbird_setup_key`` is provided, the worker installs NetBird and
    enrolls into the mesh *before* the ghostrange-worker service starts, so
    the control plane never has to reach this worker over a public IP once
    boot completes:

        install ghostrange-worker deps -> install NetBird -> `netbird up`
        -> verify connected -> scrub the setup key -> start ghostrange-worker

    ``netbird_setup_key`` must be generated/injected by the caller
    (GhostScheduler, at provisioning time, from ``Settings.netbird_worker_setup_key``
    i.e. the ``NETBIRD_WORKER_SETUP_KEY`` env var) — it is a runtime parameter,
    never a literal baked into this committed template. The key is written to
    a tmpfs path (``/run``, which itself does not survive a reboot) with
    ``0600`` permissions and is explicitly deleted (`shred -u`, falling back to
    `rm -f`) the moment `netbird up` reports a connected management session —
    it is never left sitting in a file after enrollment succeeds.

    ``netbird_peer_hostname`` (optional) pins the peer's name deterministically
    (via ``netbird up --hostname``) so the control plane's readiness gate
    (``ghostrange_api.netbird_gate``) can look the peer up by a known name
    instead of relying on the guest OS's own hostname propagation.

    When ``netbird_setup_key`` is ``None`` (the default, and what
    ``NETBIRD_ENABLED=false`` — the current setting — must always produce),
    this function's output is byte-for-byte identical to before NetBird was
    added: no NetBird block, no behavior change at all.
    """
    # Worker installs httpx only; runtime is downloaded as single file from control plane.
    netbird_write_file = ""
    netbird_runcmd = ""
    if netbird_setup_key:
        hostname_flag = f' --hostname "{netbird_peer_hostname}"' if netbird_peer_hostname else ""
        netbird_write_file = f"""
  - path: /run/ghostrange-netbird-setup.key
    permissions: '0600'
    content: |
      {netbird_setup_key}"""
        netbird_runcmd = f"""
  - curl -fsSL https://pkgs.netbird.io/install.sh -o /tmp/netbird-install.sh
  - sh /tmp/netbird-install.sh
  - netbird up --setup-key "$(cat /run/ghostrange-netbird-setup.key)"{hostname_flag}
  - bash -c 'for i in $(seq 1 30); do netbird status 2>/dev/null | grep -q "Management: Connected" && exit 0; sleep 2; done; echo "ghostrange-cloud-init: netbird did not report Connected within timeout" >&2; exit 1'
  - shred -u /run/ghostrange-netbird-setup.key || rm -f /run/ghostrange-netbird-setup.key"""

    return f"""#cloud-config
package_update: true
packages:
  - python3
  - python3-pip
  - curl
write_files:
  - path: /etc/ghostrange-worker.env
    permissions: '0600'
    content: |
      GHOSTRANGE_CONTROL_URL={control_url}
      GHOSTRANGE_BOOTSTRAP_TOKEN={bootstrap_token}
  - path: /etc/systemd/system/ghostrange-worker.service
    permissions: '0644'
    content: |
      [Unit]
      Description=GhostRange Worker
      After=network-online.target
      Wants=network-online.target
      [Service]
      Type=simple
      User=root
      EnvironmentFile=/etc/ghostrange-worker.env
      ExecStart=/usr/bin/python3 /opt/ghostrange/worker_agent.py
      Restart=on-failure
      RestartSec=5
      [Install]
      WantedBy=multi-user.target{netbird_write_file}
runcmd:
  - mkdir -p /opt/ghostrange
  - curl -fsSL "{control_url}/v1/workers/bootstrap/agent.py" -o /opt/ghostrange/worker_agent.py
  - pip3 install --break-system-packages httpx || pip3 install httpx{netbird_runcmd}
  - systemctl daemon-reload
  - systemctl enable ghostrange-worker
  - systemctl start ghostrange-worker
"""
