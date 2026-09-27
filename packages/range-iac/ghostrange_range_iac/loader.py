"""Loads a range directory (``ranges/<name>/``) into the objects `compiler.py` needs.

Directory convention for a range owned by this package:

    ranges/<name>/rangespec.yaml            RangeSpecV1 (LOGICAL topology)
    ranges/<name>/topology.yaml             RangeTopologyPlanV1 (PHYSICAL placement + edges)
    ranges/<name>/docker/<group_id>/docker-compose.yml   compose file for that physical group
    ranges/<name>/docker/<group_id>/files/**             any other file the compose file
                                                          references (nginx.conf, init.sql, ...);
                                                          written on the instance at
                                                          ``/opt/ghostrange/<relative path>``

Every ``PhysicalGroupV1.id`` declared in topology.yaml must have a matching
``docker/<group_id>/docker-compose.yml`` on disk, or loading fails loudly rather than
silently compiling an instance with no compose file.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from ghostrange_contracts.range import RangeSpecV1

from .models import RangeTopologyPlanV1

SUPPORT_FILES_TARGET_ROOT = "/opt/ghostrange"


def load_rangespec(path: Path | str) -> RangeSpecV1:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return RangeSpecV1.model_validate(raw)


def load_topology(path: Path | str) -> RangeTopologyPlanV1:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return RangeTopologyPlanV1.model_validate(raw)


def load_compose_and_support_files(
    range_dir: Path | str, topology: RangeTopologyPlanV1
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    range_dir = Path(range_dir)
    compose_by_group: dict[str, str] = {}
    support_files_by_group: dict[str, dict[str, str]] = {}

    for group in topology.physical_groups:
        group_dir = range_dir / "docker" / group.id
        compose_path = group_dir / "docker-compose.yml"
        if not compose_path.is_file():
            raise FileNotFoundError(
                f"topology declares physical group '{group.id}' but "
                f"{compose_path} does not exist"
            )
        compose_by_group[group.id] = compose_path.read_text(encoding="utf-8")

        support_files: dict[str, str] = {}
        files_dir = group_dir / "files"
        if files_dir.is_dir():
            for file_path in sorted(files_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                if "__pycache__" in file_path.parts or file_path.suffix in {".pyc", ".pyo"}:
                    continue  # stray local build artifacts, never a real support file
                rel = file_path.relative_to(files_dir).as_posix()
                target = f"{SUPPORT_FILES_TARGET_ROOT}/{rel}"
                support_files[target] = file_path.read_text(encoding="utf-8")
        support_files_by_group[group.id] = support_files

    return compose_by_group, support_files_by_group


def load_range(range_dir: Path | str) -> tuple[RangeSpecV1, RangeTopologyPlanV1, dict[str, str], dict[str, dict[str, str]]]:
    """Convenience: load everything `compiler.compile_range(...)` needs in one call."""
    range_dir = Path(range_dir)
    spec = load_rangespec(range_dir / "rangespec.yaml")
    topology = load_topology(range_dir / "topology.yaml")
    compose_by_group, support_files_by_group = load_compose_and_support_files(range_dir, topology)
    return spec, topology, compose_by_group, support_files_by_group


__all__ = [
    "load_rangespec",
    "load_topology",
    "load_compose_and_support_files",
    "load_range",
    "SUPPORT_FILES_TARGET_ROOT",
]
