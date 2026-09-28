"""Small JSON reporting helpers shared by the stage scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path | str, payload: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return target


def read_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def exit_with(status: int, message: str) -> int:
    stream = "OK" if status == 0 else "FAIL"
    print(f"[{stream}] {message}")
    return status
