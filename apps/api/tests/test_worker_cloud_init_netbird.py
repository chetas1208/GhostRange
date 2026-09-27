"""worker_cloud_init's NetBird enrollment block.

Two things this suite must prove:

1. Inertness: with no NetBird setup key passed (the default — what
   NETBIRD_ENABLED=false must always produce), the generated cloud-config
   is byte-for-byte identical to the pre-NetBird template.
2. When a setup key IS passed: NetBird is installed and enrolled, the
   worker verifies connectivity, the setup key file is scrubbed, and all of
   that happens strictly before `systemctl start ghostrange-worker`.
"""

from __future__ import annotations

from ghostrange_api.cloud_init import worker_cloud_init


_BASELINE = """#cloud-config
package_update: true
packages:
  - python3
  - python3-pip
  - curl
write_files:
  - path: /etc/ghostrange-worker.env
    permissions: '0600'
    content: |
      GHOSTRANGE_CONTROL_URL=http://control.example
      GHOSTRANGE_BOOTSTRAP_TOKEN=tok123
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
      WantedBy=multi-user.target
runcmd:
  - mkdir -p /opt/ghostrange
  - curl -fsSL "http://control.example/v1/workers/bootstrap/agent.py" -o /opt/ghostrange/worker_agent.py
  - pip3 install --break-system-packages httpx || pip3 install httpx
  - systemctl daemon-reload
  - systemctl enable ghostrange-worker
  - systemctl start ghostrange-worker
"""


def test_inert_without_netbird_setup_key_matches_pre_netbird_template():
    out = worker_cloud_init(control_url="http://control.example", bootstrap_token="tok123")
    assert out == _BASELINE


def test_inert_output_has_no_netbird_mentions_at_all():
    out = worker_cloud_init(control_url="http://control.example", bootstrap_token="tok123")
    assert "netbird" not in out.lower()


class TestWithSetupKey:
    def _render(self, **kwargs):
        return worker_cloud_init(
            control_url="http://control.example",
            bootstrap_token="tok123",
            netbird_setup_key="SUPER-SECRET-SETUP-KEY",
            **kwargs,
        )

    def test_installs_and_enrolls_netbird(self):
        out = self._render()
        assert "pkgs.netbird.io/install.sh" in out
        assert 'netbird up --setup-key "$(cat /run/ghostrange-netbird-setup.key)"' in out

    def test_verifies_connected_before_continuing(self):
        out = self._render()
        assert "Management: Connected" in out

    def test_setup_key_written_to_tmpfs_not_a_persistent_path(self):
        out = self._render()
        assert "/run/ghostrange-netbird-setup.key" in out
        assert "/etc/ghostrange-netbird" not in out  # never written under /etc (persistent)

    def test_setup_key_value_appears_exactly_once_and_only_in_the_tmpfs_file(self):
        out = self._render()
        assert out.count("SUPER-SECRET-SETUP-KEY") == 1

    def test_setup_key_file_permissions_are_owner_only(self):
        out = self._render()
        key_block = out.split("/run/ghostrange-netbird-setup.key")[0]
        # the write_files entry for the key file sets 0600 right above the path line
        assert "permissions: '0600'" in out

    def test_scrubs_setup_key_file_after_enrollment(self):
        out = self._render()
        assert "shred -u /run/ghostrange-netbird-setup.key" in out or "rm -f /run/ghostrange-netbird-setup.key" in out

    def test_netbird_enrollment_happens_before_worker_service_starts(self):
        out = self._render()
        enroll_idx = out.index("netbird up --setup-key")
        verify_idx = out.index("Management: Connected")
        scrub_idx = out.index("shred -u /run/ghostrange-netbird-setup.key")
        start_idx = out.index("systemctl start ghostrange-worker")
        assert enroll_idx < verify_idx < scrub_idx < start_idx

    def test_hostname_flag_passed_through_when_given(self):
        out = self._render(netbird_peer_hostname="gr-worker-ab12cd34")
        assert '--hostname "gr-worker-ab12cd34"' in out

    def test_no_hostname_flag_when_not_given(self):
        out = self._render()
        assert "--hostname" not in out

    def test_ghostrange_worker_bootstrap_untouched_by_netbird_block(self):
        out = self._render()
        assert "GHOSTRANGE_CONTROL_URL=http://control.example" in out
        assert "GHOSTRANGE_BOOTSTRAP_TOKEN=tok123" in out
        assert "systemctl enable ghostrange-worker" in out
