"""CLI: ghostrange-verify <bundle.json>"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ghostrange_contracts.ghostledger_m7 import GhostBundleV1

from .verify import verify_bundle


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) < 2 or argv[0] != "verify":
        print("usage: ghostrange-verify verify <bundle.json> [--trust-pem path]", file=sys.stderr)
        return 2
    path = Path(argv[1])
    trust: dict[str, str] = {}
    if "--trust-pem" in argv:
        i = argv.index("--trust-pem")
        pem = Path(argv[i + 1]).read_text()
        trust["ghostrange-dev"] = pem
    data = json.loads(path.read_text())
    bundle = GhostBundleV1.model_validate(data.get("bundle", data))
    if not trust and "trusted_public_keys" in data:
        trust = data["trusted_public_keys"]
    result = verify_bundle(bundle, trusted_public_keys=trust)
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    return 0 if result.verified_integrity else 1


if __name__ == "__main__":
    raise SystemExit(main())
