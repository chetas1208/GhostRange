#!/usr/bin/env python3
"""M10 live resource lease — only one integration run may hold live budget."""

from __future__ import annotations

import fcntl
import sys
from pathlib import Path

LOCK = Path("/tmp/ghostrange-m10-live.lock")


def acquire() -> None:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    fh = LOCK.open("w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Another live integration holds the lease", file=sys.stderr)
        raise SystemExit(1)
    fh.write("leased\n")
    fh.flush()


if __name__ == "__main__":
    acquire()
    print("Live lease acquired")
