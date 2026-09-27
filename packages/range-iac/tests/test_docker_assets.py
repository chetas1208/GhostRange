"""Sanity checks on the real, checked-in docker-compose/app-stub files for
ghostrange-auth-lab-v1 -- these are not live-Docker tests (no docker daemon assumed
in CI or in this sandbox), just proof the files are syntactically well-formed and
internally consistent with the topology's physical-group convention (see
loader.py's docstring for the docker/<group_id>/... layout)."""

from __future__ import annotations

import ast
from pathlib import Path

import yaml


def test_docker_compose_is_valid_yaml_with_expected_services(range_dir: Path):
    compose_path = range_dir / "docker" / "vm-1" / "docker-compose.yml"
    doc = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    assert set(doc["services"]) == {"gateway", "api", "auth", "data-store"}
    assert doc["services"]["gateway"]["ports"] == ["80:80"]
    # api/auth/data-store must NOT publish host ports -- only reachable via the
    # compose network, matching topology.yaml's declaration that only gw01 has an
    # INTERNET-sourced edge.
    for svc in ("api", "auth", "data-store"):
        assert "ports" not in doc["services"][svc]


def test_app_stub_files_are_syntactically_valid_python(range_dir: Path):
    for svc in ("api", "auth"):
        path = range_dir / "docker" / "vm-1" / "files" / svc / "app.py"
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_nginx_conf_proxies_to_api(range_dir: Path):
    conf = (range_dir / "docker" / "vm-1" / "files" / "gateway" / "nginx.conf").read_text(encoding="utf-8")
    assert "proxy_pass http://api:8080/" in conf


def test_bind_mount_targets_match_loader_convention(range_dir: Path):
    """Every bind-mount source path under /opt/ghostrange/... in the compose file
    must correspond to a real file under docker/vm-1/files/, per loader.py's
    files/<rel> -> /opt/ghostrange/<rel> convention -- otherwise cloud-init would
    reference a file that was never written."""
    compose_path = range_dir / "docker" / "vm-1" / "docker-compose.yml"
    doc = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    files_root = range_dir / "docker" / "vm-1" / "files"

    for svc in doc["services"].values():
        for mount in svc.get("volumes", []):
            src = mount.split(":")[0]
            if not src.startswith("/opt/ghostrange/"):
                continue  # named volume, not a support file
            rel = src[len("/opt/ghostrange/") :]
            assert (files_root / rel).is_file(), f"compose references {src} but {files_root / rel} is missing"
