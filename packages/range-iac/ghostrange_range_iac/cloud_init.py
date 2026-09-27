"""Renders real `#cloud-config` user-data for a physical Vultr instance.

Two distinct render modes, per ADR-006's "two compilation modes" consequence
(docs/architecture/ADR-006-vultr-integration.md, "Consequences" section) and
docs/adr/ADR-M2-RANGE-PROVISIONING.md's teardown/reproducibility discussion:

- ``mode="base"``: first boot of a fresh instance from a bare ``os_id``. Docker isn't
  installed yet, so this cloud-init installs it (Vultr's own docs say cloud-init
  processing takes on the order of 10 minutes -- this is the cost that mode="base"
  pays, once, before that instance gets snapshotted into a golden image).
- ``mode="fork"``: boot of an instance restored from a pre-warmed golden
  ``snapshot_id`` that already has docker + pulled/built images baked in. This
  cloud-init skips the docker install entirely and just (re)asserts the compose
  file contents and brings the stack up -- fast, because the slow part already
  happened once when the golden snapshot was built.

Both modes are real, working cloud-init documents, not templates-of-templates --
what you get back from ``render_cloud_init`` is exactly what would be handed to
Vultr's ``user_data`` field (base64-encoding it is the transport client's job, not
this module's -- see provider_interface.py's docstring).
"""

from __future__ import annotations

from typing import Literal

import yaml


class _LiteralStr(str):
    """Marker so PyYAML emits this string with block ('|') style, not quoted/escaped."""


def _literal_str_representer(dumper: yaml.Dumper, data: _LiteralStr):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")


yaml.add_representer(_LiteralStr, _literal_str_representer)


def render_cloud_init(
    *,
    compose_yaml: str,
    support_files: dict[str, str],
    mode: Literal["base", "fork"] = "base",
    compose_path: str = "/opt/ghostrange/docker-compose.yml",
) -> str:
    """Build a full `#cloud-config` document as a string.

    Args:
        compose_yaml: contents of the docker-compose file for whatever services this
            physical instance runs (may be a subset of a range's full compose file if
            a range ever spans multiple physical groups; for ghostrange-auth-lab-v1's
            single-VM M2 layout it's the whole file).
        support_files: {absolute path -> file content} for anything else the compose
            file references (nginx.conf, init.sql, ...). Written before compose-up.
        mode: "base" (bare OS, install docker) or "fork" (snapshot already has
            docker + images; just bring the stack up).
        compose_path: where the compose file is written on the instance.
    """
    write_files = [
        {
            "path": compose_path,
            "owner": "root:root",
            "permissions": "0644",
            "content": _LiteralStr(compose_yaml),
        }
    ]
    for path, content in support_files.items():
        write_files.append(
            {
                "path": path,
                "owner": "root:root",
                "permissions": "0644",
                "content": _LiteralStr(content),
            }
        )

    runcmd: list[list[str] | str] = []

    if mode == "base":
        # Docker Engine is not present on a bare os_id boot. Vultr's own cloud-init
        # docs (docs/research/VULTR.md section 4) note this whole process takes
        # ~10 minutes; this is the one-time cost a base-mode boot pays, before it
        # gets snapshotted into the golden image forks restore from instead.
        runcmd.append(["curl", "-fsSL", "https://get.docker.com", "-o", "/tmp/get-docker.sh"])
        runcmd.append(["sh", "/tmp/get-docker.sh"])
        runcmd.append(["systemctl", "enable", "--now", "docker"])
    # mode == "fork": docker is already installed and images already pulled/built
    # inside the golden snapshot this instance was restored from -- nothing to do
    # here but bring the (possibly refreshed) compose file up.

    runcmd.append(["docker", "compose", "-f", compose_path, "up", "-d", "--remove-orphans"])

    doc = {
        "package_update": mode == "base",
        "write_files": write_files,
        "runcmd": runcmd,
    }

    body = yaml.dump(doc, sort_keys=False, default_flow_style=False, width=100)
    return f"#cloud-config\n{body}"


__all__ = ["render_cloud_init"]
