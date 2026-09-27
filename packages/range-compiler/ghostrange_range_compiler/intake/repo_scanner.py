"""Heuristic repository scanner — the first pass of the GitHub-as-input
feature (see ``docs/architecture/PRODUCT.md`` and this package's
``docs/architecture/RANGE_COMPILER.md``).

Given a directory on disk (already cloned, or a fixture in tests), walk the
tree looking for structural signals and produce a
``ghostrange_contracts.derived_system_model.DerivedSystemModelV1``:

- ``docker-compose.yml``/``.yaml`` — services, images, build contexts,
  published ports, ``depends_on`` edges.
- ``Dockerfile`` — base image (``FROM``), exposed ports (``EXPOSE``).
- Kubernetes manifests — any YAML doc with
  ``kind: Deployment|StatefulSet|DaemonSet|CronJob|Job|Service``.
- Terraform ``*.tf`` — ``resource "TYPE" "NAME"`` blocks.
- Package manifests (``package.json``, ``pyproject.toml``, ``go.mod``, ...)
  — language identification per directory/service boundary.
- OpenAPI/Swagger specs — marks the owning service as an external
  interface.
- ``.env.example``/``.env.template`` files — configuration surface only;
  values are read solely to look for *references to other service names*
  (never stored, never treated as real secrets).

This is intentionally heuristic/best-effort file-and-pattern matching, not
AST-level static analysis. Every derived service/edge carries at least one
``DerivationProvenanceV1`` entry naming the file and rule that produced it,
so the result is auditable rather than a black box.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ghostrange_contracts.derived_system_model import (
    DerivationConfidence,
    DerivationProvenanceV1,
    DerivationSourceKind,
    DerivedDependencyEdgeV1,
    DerivedServiceRole,
    DerivedServiceV1,
    DerivedSystemModelV1,
    RepoScanSummaryV1,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IGNORED_DIR_NAMES = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    "target",
    ".next",
    ".terraform",
    ".pytest_cache",
    "coverage",
    ".mypy_cache",
    "egg-info",
}

_COMPOSE_FILENAMES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
_OPENAPI_FILENAMES = {
    "openapi.yaml",
    "openapi.yml",
    "openapi.json",
    "swagger.yaml",
    "swagger.yml",
    "swagger.json",
}
_PACKAGE_MANIFEST_LANGUAGES = {
    "package.json": "javascript/typescript",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "go.mod": "go",
    "cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
    "gemfile": "ruby",
    "composer.json": "php",
}
_ENV_TEMPLATE_RE = re.compile(r"^\.env(?:\.[A-Za-z0-9_-]+)?\.(?:example|template|sample)$", re.IGNORECASE)
_ENV_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")

_EXPOSE_RE = re.compile(r"^\s*EXPOSE\s+([0-9]+)", re.IGNORECASE | re.MULTILINE)
_FROM_RE = re.compile(r"^\s*FROM\s+([^\s]+)", re.IGNORECASE | re.MULTILINE)
_TF_RESOURCE_RE = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"')

_K8S_WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "CronJob", "Job"}

_ROLE_NAME_HINTS: list[tuple[re.Pattern[str], DerivedServiceRole]] = [
    (re.compile(r"auth|iam|identity|sso|login", re.I), DerivedServiceRole.AUTH),
    (re.compile(r"gateway|proxy|nginx|envoy|traefik|ingress|kong", re.I), DerivedServiceRole.GATEWAY),
    (
        re.compile(
            r"postgres|mysql|maria|mongo|sqlite|cockroach|cassandra|dynamodb|database|rds|sql"
            r"|(?<![a-zA-Z])db(?![a-zA-Z])",
            re.I,
        ),
        DerivedServiceRole.DATABASE,
    ),
    (re.compile(r"redis|memcached|\bcache\b|elasticache", re.I), DerivedServiceRole.CACHE),
    (re.compile(r"rabbitmq|kafka|\bqueue\b|nats|\bsqs\b|pubsub|broker", re.I), DerivedServiceRole.QUEUE),
    (re.compile(r"frontend|web-?ui|\bclient\b|webapp|\bui\b", re.I), DerivedServiceRole.FRONTEND),
    (re.compile(r"worker|\bjobs?\b|consumer|scheduler", re.I), DerivedServiceRole.WORKER),
    (re.compile(r"\bapi\b|backend|\bservice\b|server", re.I), DerivedServiceRole.API),
]

DATASTORE_ROLES = {DerivedServiceRole.DATABASE, DerivedServiceRole.CACHE, DerivedServiceRole.QUEUE}


def _infer_role(*texts: str) -> tuple[DerivedServiceRole, DerivationConfidence]:
    """Weak name/image-based role guess. Always low-to-medium confidence —
    never claimed as certain (see DerivedSystemModelV1.confidence_disclaimer)."""
    for pattern, role in _ROLE_NAME_HINTS:
        for text in texts:
            if text and pattern.search(text):
                return role, DerivationConfidence.MEDIUM
    return DerivedServiceRole.UNKNOWN, DerivationConfidence.LOW


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _resolve_context_dir(root: Path, build_context: str) -> Path | None:
    try:
        return (root / build_context).resolve()
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Scan state
# ---------------------------------------------------------------------------


@dataclass
class _ScanState:
    services: dict[str, DerivedServiceV1] = field(default_factory=dict)
    edges: list[DerivedDependencyEdgeV1] = field(default_factory=list)
    files_scanned: int = 0
    files_relevant: int = 0
    warnings: list[str] = field(default_factory=list)

    def get_or_create(self, name: str) -> DerivedServiceV1:
        svc = self.services.get(name)
        if svc is None:
            svc = DerivedServiceV1(name=name)
            self.services[name] = svc
        return svc

    def find_by_build_context(self, root: Path, directory: Path) -> DerivedServiceV1 | None:
        target = directory.resolve()
        for svc in self.services.values():
            if svc.build_context:
                resolved = _resolve_context_dir(root, svc.build_context)
                if resolved == target:
                    return svc
        return None

    def apply_role(self, svc: DerivedServiceV1, role: DerivedServiceRole, confidence: DerivationConfidence) -> None:
        if role == DerivedServiceRole.UNKNOWN:
            return
        if svc.inferred_role == DerivedServiceRole.UNKNOWN or (
            confidence == DerivationConfidence.MEDIUM and svc.role_confidence == DerivationConfidence.LOW
        ):
            svc.inferred_role = role
            svc.role_confidence = confidence


def _add_provenance(
    svc: DerivedServiceV1,
    *,
    source_kind: DerivationSourceKind,
    source_path: str,
    locator: str,
    rule: str,
    note: str,
) -> None:
    svc.provenance.append(
        DerivationProvenanceV1(
            source_kind=source_kind,
            source_path=source_path,
            locator=locator,
            rule=rule,
            note=note,
        )
    )


# ---------------------------------------------------------------------------
# Per-signal handlers
# ---------------------------------------------------------------------------


def _parse_compose_port(entry: Any) -> int | None:
    """Best-effort extraction of a host-facing port number from a compose
    ``ports:`` entry, which may be an int, ``"8080:80"``, ``"80"``, or a
    long-form mapping dict."""
    try:
        if isinstance(entry, int):
            return entry
        if isinstance(entry, dict):
            val = entry.get("published") or entry.get("target")
            return int(val) if val is not None else None
        if isinstance(entry, str):
            head = entry.split(":")[0].strip()
            return int(head) if head.isdigit() else None
    except (ValueError, TypeError):
        return None
    return None


def _handle_compose_file(path: Path, root: Path, state: _ScanState) -> None:
    rel = _relative(path, root)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
    except yaml.YAMLError as exc:
        state.warnings.append(f"{rel}: could not parse YAML ({exc})")
        return
    services = data.get("services") if isinstance(data, dict) else None
    if not isinstance(services, dict):
        return
    state.files_relevant += 1

    for name, svc_def in services.items():
        if not isinstance(svc_def, dict):
            continue
        name = str(name)
        svc = state.get_or_create(name)

        image = svc_def.get("image")
        if image:
            svc.image = str(image)

        build = svc_def.get("build")
        if isinstance(build, str):
            svc.build_context = build
        elif isinstance(build, dict) and build.get("context"):
            svc.build_context = str(build["context"])

        published_any = False
        for entry in svc_def.get("ports") or []:
            port_num = _parse_compose_port(entry)
            if port_num is not None:
                svc.ports.append(port_num)
                published_any = True
        if published_any:
            svc.is_external_interface = True

        role, conf = _infer_role(str(image or ""), name)
        state.apply_role(svc, role, conf)

        _add_provenance(
            svc,
            source_kind=DerivationSourceKind.DOCKER_COMPOSE,
            source_path=rel,
            locator=f"services.{name}",
            rule="compose_service_block",
            note=f"derived from {rel} service block `{name}`",
        )

        for dep in svc_def.get("depends_on") or []:
            dep_name = dep if isinstance(dep, str) else str(dep)
            state.edges.append(
                DerivedDependencyEdgeV1(
                    from_service=name,
                    to_service=dep_name,
                    relationship="depends_on",
                    provenance=[
                        DerivationProvenanceV1(
                            source_kind=DerivationSourceKind.DOCKER_COMPOSE,
                            source_path=rel,
                            locator=f"services.{name}.depends_on",
                            rule="compose_depends_on",
                            note=f"derived from {rel} `{name}.depends_on` -> `{dep_name}`",
                        )
                    ],
                )
            )


def _handle_dockerfile(path: Path, root: Path, state: _ScanState) -> None:
    rel = _relative(path, root)
    text = path.read_text(encoding="utf-8", errors="replace")
    state.files_relevant += 1

    existing = state.find_by_build_context(root, path.parent)
    name = existing.name if existing else (path.parent.name if path.parent != root else (root.name or "app"))
    svc = existing or state.get_or_create(name)

    from_match = _FROM_RE.search(text)
    base_image = from_match.group(1) if from_match else None
    if base_image and not svc.image:
        svc.image = base_image

    for match in _EXPOSE_RE.finditer(text):
        try:
            svc.ports.append(int(match.group(1)))
            svc.is_external_interface = True
        except ValueError:
            continue

    role, conf = _infer_role(base_image or "", name)
    state.apply_role(svc, role, conf)

    _add_provenance(
        svc,
        source_kind=DerivationSourceKind.DOCKERFILE,
        source_path=rel,
        locator="FROM/EXPOSE",
        rule="dockerfile_directives",
        note=f"derived from {rel} (FROM {base_image or 'unknown'})",
    )


def _handle_k8s_file(path: Path, root: Path, state: _ScanState) -> bool:
    rel = _relative(path, root)
    try:
        docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8", errors="replace")) if d]
    except yaml.YAMLError as exc:
        state.warnings.append(f"{rel}: could not parse YAML ({exc})")
        return False

    matched = False
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind")
        if kind not in _K8S_WORKLOAD_KINDS and kind != "Service":
            continue
        matched = True
        name = str(((doc.get("metadata") or {}).get("name")) or "unnamed")
        svc = state.get_or_create(name)

        if kind in _K8S_WORKLOAD_KINDS:
            containers = (((doc.get("spec") or {}).get("template") or {}).get("spec") or {}).get("containers") or []
            for container in containers:
                if not isinstance(container, dict):
                    continue
                image = container.get("image")
                if image and not svc.image:
                    svc.image = str(image)
                for port_def in container.get("ports") or []:
                    if isinstance(port_def, dict):
                        container_port = port_def.get("containerPort")
                        if isinstance(container_port, int):
                            svc.ports.append(container_port)
            role, conf = _infer_role(svc.image or "", name)
        else:  # Service
            for port_def in (doc.get("spec") or {}).get("ports") or []:
                if isinstance(port_def, dict):
                    port_val = port_def.get("port")
                    if isinstance(port_val, int):
                        svc.ports.append(port_val)
            if (doc.get("spec") or {}).get("type") in ("LoadBalancer", "NodePort"):
                svc.is_external_interface = True
            role, conf = _infer_role(name)

        state.apply_role(svc, role, conf)
        _add_provenance(
            svc,
            source_kind=DerivationSourceKind.KUBERNETES_MANIFEST,
            source_path=rel,
            locator=f"{kind}/{name}",
            rule="k8s_manifest_kind",
            note=f"derived from {rel} `kind: {kind}`, `metadata.name: {name}`",
        )
    return matched


def _handle_terraform_file(path: Path, root: Path, state: _ScanState) -> bool:
    rel = _relative(path, root)
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(_TF_RESOURCE_RE.finditer(text))
    if not matches:
        return False

    for match in matches:
        res_type, res_name = match.group(1), match.group(2)
        svc = state.get_or_create(res_name)
        role, conf = _infer_role(res_type, res_name)
        state.apply_role(svc, role, conf)
        if re.search(r"lb|gateway|alb|elb|api_gateway", res_type, re.I):
            svc.is_external_interface = True
        _add_provenance(
            svc,
            source_kind=DerivationSourceKind.TERRAFORM,
            source_path=rel,
            locator=f'resource "{res_type}" "{res_name}"',
            rule="terraform_resource_block",
            note=f"derived from {rel} resource block `{res_type}.{res_name}`",
        )
    return True


def _handle_package_manifest(path: Path, root: Path, state: _ScanState, language: str) -> None:
    rel = _relative(path, root)
    dir_name = path.parent.name if path.parent != root else (root.name or "app")

    existing = state.find_by_build_context(root, path.parent)
    svc = existing or state.services.get(dir_name) or state.get_or_create(dir_name)

    if not svc.language:
        svc.language = language

    role, conf = _infer_role(dir_name)
    state.apply_role(svc, role, conf)

    _add_provenance(
        svc,
        source_kind=DerivationSourceKind.PACKAGE_MANIFEST,
        source_path=rel,
        locator=path.name,
        rule="package_manifest_language",
        note=f"derived from {rel} (language: {language})",
    )


def _handle_openapi_file(path: Path, root: Path, state: _ScanState) -> None:
    rel = _relative(path, root)
    dir_name = path.parent.name if path.parent != root else (root.name or "app")

    svc = state.find_by_build_context(root, path.parent) or state.services.get(dir_name) or state.get_or_create(
        dir_name
    )
    svc.is_external_interface = True
    _add_provenance(
        svc,
        source_kind=DerivationSourceKind.OPENAPI_SPEC,
        source_path=rel,
        locator="spec_root",
        rule="openapi_spec_present",
        note=f"derived from {rel} (OpenAPI/Swagger spec present)",
    )


def _handle_env_template(path: Path, root: Path, state: _ScanState) -> None:
    """Configuration-surface signal only. Values are inspected solely to
    look for other declared service names (e.g. ``AUTH_URL=http://auth:8080``)
    — never persisted, never treated as real secrets, never executed."""
    rel = _relative(path, root)
    dir_name = path.parent.name if path.parent != root else (root.name or "app")
    owner = state.find_by_build_context(root, path.parent) or state.services.get(dir_name)

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return

    referenced: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ENV_LINE_RE.match(stripped)
        if not match:
            continue
        _key, value = match.groups()
        for candidate_name in state.services:
            if candidate_name and re.search(rf"(^|[/@.:]){re.escape(candidate_name)}([:/.]|$)", value):
                referenced.add(candidate_name)

    if owner:
        for target_name in sorted(referenced):
            if target_name == owner.name:
                continue
            state.edges.append(
                DerivedDependencyEdgeV1(
                    from_service=owner.name,
                    to_service=target_name,
                    relationship="env_reference",
                    provenance=[
                        DerivationProvenanceV1(
                            source_kind=DerivationSourceKind.ENV_TEMPLATE,
                            source_path=rel,
                            locator="env_value_hostname_match",
                            rule="env_reference_heuristic",
                            note=f"derived from {rel}: a config value appears to reference service `{target_name}`",
                        )
                    ],
                )
            )


# ---------------------------------------------------------------------------
# Top-level scan
# ---------------------------------------------------------------------------


def scan_directory(root: Path, *, repository_url: str = "", branch: str = "") -> DerivedSystemModelV1:
    """Walk ``root`` and produce a best-effort :class:`DerivedSystemModelV1`.

    Processing order matters: compose/Dockerfile/k8s/Terraform run first so
    the service inventory exists before package manifests, OpenAPI specs,
    and ``.env`` templates try to attach themselves to (or reference) known
    services.
    """
    root = root.resolve()
    state = _ScanState()

    compose_paths: list[Path] = []
    dockerfile_paths: list[Path] = []
    k8s_candidate_paths: list[Path] = []
    terraform_paths: list[Path] = []
    package_manifest_paths: list[tuple[Path, str]] = []
    openapi_paths: list[Path] = []
    env_template_paths: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIR_NAMES and not d.startswith(".git"))
        for fname in sorted(filenames):
            state.files_scanned += 1
            fpath = Path(dirpath) / fname
            lower = fname.lower()
            if lower in _COMPOSE_FILENAMES:
                compose_paths.append(fpath)
            elif lower == "dockerfile" or lower.startswith("dockerfile."):
                dockerfile_paths.append(fpath)
            elif lower in _OPENAPI_FILENAMES:
                openapi_paths.append(fpath)
            elif lower in _PACKAGE_MANIFEST_LANGUAGES:
                package_manifest_paths.append((fpath, _PACKAGE_MANIFEST_LANGUAGES[lower]))
            elif fname.endswith(".tf"):
                terraform_paths.append(fpath)
            elif _ENV_TEMPLATE_RE.match(fname):
                env_template_paths.append(fpath)
            elif lower.endswith(".yaml") or lower.endswith(".yml"):
                k8s_candidate_paths.append(fpath)

    for p in compose_paths:
        _handle_compose_file(p, root, state)
    for p in dockerfile_paths:
        _handle_dockerfile(p, root, state)
    for p in k8s_candidate_paths:
        if p not in compose_paths and _handle_k8s_file(p, root, state):
            state.files_relevant += 1
    for p in terraform_paths:
        if _handle_terraform_file(p, root, state):
            state.files_relevant += 1
    for p, lang in package_manifest_paths:
        _handle_package_manifest(p, root, state, lang)
        state.files_relevant += 1
    for p in openapi_paths:
        _handle_openapi_file(p, root, state)
        state.files_relevant += 1
    for p in env_template_paths:
        _handle_env_template(p, root, state)
        state.files_relevant += 1

    services = [state.services[name] for name in sorted(state.services)]
    data_stores = sum(1 for s in services if s.inferred_role in DATASTORE_ROLES)
    external = sum(1 for s in services if s.is_external_interface)

    summary = RepoScanSummaryV1(
        files_scanned=state.files_scanned,
        files_relevant=state.files_relevant,
        services_identified=len(services),
        data_stores_identified=data_stores,
        external_interfaces_identified=external,
        warnings=state.warnings,
    )

    return DerivedSystemModelV1(
        repository_url=repository_url,
        branch=branch,
        services=services,
        dependency_edges=state.edges,
        summary=summary,
    )


__all__ = ["scan_directory", "IGNORED_DIR_NAMES", "DATASTORE_ROLES"]
