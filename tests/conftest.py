"""Test-suite configuration.

Adds the package ``scripts`` directory to ``sys.path`` so the tests can import
the shared helpers, and exposes frequently used paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Keep interpreter bytecode caches out of the distributed tree when the suite
# is run directly, so that verification cannot modify package content.
sys.dont_write_bytecode = True

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

if str(PACKAGE_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT / "scripts"))

from utils import paths  # noqa: E402


@pytest.fixture(scope="session")
def package_root() -> Path:
    return paths.PACKAGE_ROOT


@pytest.fixture(scope="session")
def expected_hashes() -> dict:
    from utils.hashing import read_json

    return read_json(paths.CONFIG_DIR / "expected_hashes.json")


@pytest.fixture(scope="session")
def expected_outputs() -> dict:
    from utils.hashing import read_json

    return read_json(paths.CONFIG_DIR / "expected_outputs.json")


@pytest.fixture(scope="session")
def frozen_config() -> dict:
    from utils.hashing import read_json

    return read_json(paths.CONFIG_DIR / "frozen_analysis_config.json")
