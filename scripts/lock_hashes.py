#!/usr/bin/env python3
"""Regenerate ``requirements.lock`` with sha256 hashes from the PyPI JSON API.

Reads the current pin list (``name==version`` lines) from
``requirements.lock`` and rewrites it with the full per-release hash set
(pip-compile layout) so CI can install with ``--require-hashes``
(SonarCloud S8544). Requires network access to pypi.org.

Usage:  python scripts/lock_hashes.py
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "requirements.lock"


def fetch_hashes(name: str, version: str) -> list[str]:
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    hashes = sorted(
        {f["digests"]["sha256"] for f in data["urls"] if f.get("digests", {}).get("sha256")}
    )
    if not hashes:
        raise SystemExit(f"error: no sha256 hashes published for {name}=={version}")
    return hashes


def render_block(name: str, version: str, hashes: list[str]) -> str:
    lines = [f"{name}=={version} \\"]
    for i, h in enumerate(hashes):
        tail = " \\" if i < len(hashes) - 1 else ""
        lines.append(f"    --hash=sha256:{h}{tail}")
    return "\n".join(lines)


def main() -> None:
    pins = [
        line.split("==")
        for line in LOCK.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    blocks = [render_block(n, v, fetch_hashes(n, v)) for n, v in pins]
    header = (
        "# Lockfile with PEP 503 sha256 hashes for hash-pinned installs (SonarCloud S8544).\n"
        "# Hashes are the full per-release file set from the PyPI JSON API; pip verifies\n"
        "# whichever file it fetches. Regenerate with: scripts/lock_hashes.py (or manual fetch).\n"
    )
    LOCK.write_text(header + "\n".join(blocks) + "\n", encoding="utf-8")
    print(f"wrote {LOCK} ({len(blocks)} packages)")


if __name__ == "__main__":
    main()
