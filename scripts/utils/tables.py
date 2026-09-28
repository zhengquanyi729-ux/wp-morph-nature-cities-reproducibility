"""Deterministic CSV writing and value-level comparison helpers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .hashing import sha256_file

# Frozen writing dialect: UTF-8 with BOM, no index column, %.12g float format.
CSV_ENCODING = "utf-8-sig"
CSV_FLOAT_FORMAT = "%.12g"
# The frozen CSV files use Windows CRLF line endings. pandas' default line
# terminator is os.linesep, which would silently produce LF on Linux and break
# byte-level identity with the frozen files. The terminator is therefore pinned
# explicitly so that output is byte-identical on every operating system.
CSV_LINE_TERMINATOR = "\r\n"


def read_frozen_csv(path: Path | str) -> pd.DataFrame:
    return pd.read_csv(path, encoding=CSV_ENCODING)


def write_csv(df: pd.DataFrame, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(
        target,
        index=False,
        encoding=CSV_ENCODING,
        float_format=CSV_FLOAT_FORMAT,
        lineterminator=CSV_LINE_TERMINATOR,
    )
    return target


def _normalise(value: Any) -> Any:
    if isinstance(value, (np.floating, float)):
        if math.isnan(float(value)):
            return "nan"
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def frames_equal(left: pd.DataFrame, right: pd.DataFrame, ignore_index: bool = True) -> bool:
    """Value-level equality with the same column order and row order."""
    if list(left.columns) != list(right.columns):
        return False
    if len(left) != len(right):
        return False
    a = left.reset_index(drop=True) if ignore_index else left
    b = right.reset_index(drop=True) if ignore_index else right
    for column in a.columns:
        for x, y in zip(a[column].tolist(), b[column].tolist()):
            nx, ny = _normalise(x), _normalise(y)
            if isinstance(nx, float) or isinstance(ny, float):
                if isinstance(nx, str) or isinstance(ny, str):
                    if nx != ny:
                        return False
                    continue
                if not math.isclose(float(nx), float(ny), rel_tol=0.0, abs_tol=1e-12):
                    return False
            elif nx != ny:
                return False
    return True


def compare_to_frozen(
    reproduced: Path | str,
    frozen: Path | str,
) -> dict[str, Any]:
    """Compare a reproduced table with the frozen table.

    Returns a machine-readable comparison record. Byte identity is reported as
    a bonus; value-level identity is the acceptance criterion.
    """
    reproduced = Path(reproduced)
    frozen = Path(frozen)
    record: dict[str, Any] = {
        "reproduced_file": reproduced.name,
        "reproduced_sha256": sha256_file(reproduced),
        "frozen_sha256": sha256_file(frozen),
    }
    record["byte_identical"] = record["reproduced_sha256"] == record["frozen_sha256"]

    a = read_frozen_csv(reproduced)
    b = read_frozen_csv(frozen)
    record["row_count_reproduced"] = int(len(a))
    record["row_count_frozen"] = int(len(b))
    record["columns_match"] = list(a.columns) == list(b.columns)
    record["values_match"] = record["columns_match"] and frames_equal(a, b)
    record["status"] = "PASS" if record["values_match"] else "FAIL"
    return record
