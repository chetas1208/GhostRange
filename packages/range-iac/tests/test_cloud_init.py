from __future__ import annotations

import yaml
from ghostrange_range_iac.cloud_init import render_cloud_init


def test_base_mode_installs_docker_and_writes_compose():
    out = render_cloud_init(
        compose_yaml="services:\n  x:\n    image: alpine\n",
        support_files={"/opt/ghostrange/foo.conf": "hello\n"},
        mode="base",
    )
    assert out.startswith("#cloud-config\n")

    parsed = yaml.safe_load(out[len("#cloud-config\n") :])
    assert parsed["package_update"] is True

    paths = {f["path"] for f in parsed["write_files"]}
    assert "/opt/ghostrange/docker-compose.yml" in paths
    assert "/opt/ghostrange/foo.conf" in paths

    flat_runcmd = [" ".join(c) if isinstance(c, list) else c for c in parsed["runcmd"]]
    assert any("get-docker.sh" in c for c in flat_runcmd)
    assert any("docker compose" in c for c in flat_runcmd)


def test_fork_mode_skips_docker_install():
    out = render_cloud_init(
        compose_yaml="services:\n  x:\n    image: alpine\n",
        support_files={},
        mode="fork",
    )
    parsed = yaml.safe_load(out[len("#cloud-config\n") :])
    assert parsed["package_update"] is False

    flat_runcmd = [" ".join(c) if isinstance(c, list) else c for c in parsed["runcmd"]]
    assert not any("get-docker.sh" in c for c in flat_runcmd)
    assert any("docker compose" in c for c in flat_runcmd)


def test_rendered_yaml_is_well_formed_and_content_is_preserved():
    compose = "services:\n  gateway:\n    image: nginx:1.27-alpine\n"
    out = render_cloud_init(compose_yaml=compose, support_files={}, mode="base")
    parsed = yaml.safe_load(out[len("#cloud-config\n") :])
    written = next(f for f in parsed["write_files"] if f["path"] == "/opt/ghostrange/docker-compose.yml")
    assert written["content"] == compose
