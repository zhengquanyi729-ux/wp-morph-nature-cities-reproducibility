"""SHA256 helpers. Digests are uppercase hexadecimal, matching the frozen records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def read_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_record(path: Path | str, role: str) -> dict[str, Any]:
    p = Path(path)
    return {
        "role": role,
        "file_name": p.name,
        "relative_path": None,
        "size_bytes": p.stat().st_size,
        "sha256": sha256_file(p),
    }
