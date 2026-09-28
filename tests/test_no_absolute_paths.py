"""No runnable journal-facing file may contain a user-specific absolute path."""

from __future__ import annotations

import re

from utils import paths

DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]")
FORBIDDEN_SUBSTRINGS = (
    "china_meld",
    "/Users/",
    "\\Users\\",
    "C:\\",
    "C:/",
)


def _runnable_files():
    yield paths.PACKAGE_ROOT / "run_all.py"
    yield paths.PACKAGE_ROOT / "run_all.bat"
    yield paths.PACKAGE_ROOT / "run_all.ps1"
    for path in sorted((paths.PACKAGE_ROOT / "scripts").rglob("*.py")):
        yield path


def test_no_absolute_paths_in_runnable_files():
    offenders = []
    for path in _runnable_files():
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(paths.PACKAGE_ROOT).as_posix()
        if DRIVE_PATH.search(text):
            offenders.append(f"drive-qualified path in {relative}")
        for token in FORBIDDEN_SUBSTRINGS:
            if token in text:
                offenders.append(f"forbidden substring {token!r} in {relative}")

    # "run_all.bat" and "run_all.ps1" legitimately reference the drive only through
    # %~dp0 / $MyInvocation, so any hit above is a genuine problem.
    assert not offenders, offenders


def test_package_root_is_derived_from_file_location():
    text = (paths.PACKAGE_ROOT / "scripts" / "utils" / "paths.py").read_text(encoding="utf-8")
    assert "Path(__file__)" in text
    assert ".resolve()" in text
    assert "run_all.py" in text


def test_original_frozen_scripts_are_labelled_as_provenance():
    readme = (paths.PACKAGE_ROOT / "original_frozen_scripts" / "README.md").read_text(
        encoding="utf-8"
    )
    lowered = readme.lower()
    assert "non-runnable" in lowered
    assert "provenance" in lowered
