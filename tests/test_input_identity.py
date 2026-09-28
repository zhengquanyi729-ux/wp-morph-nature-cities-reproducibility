"""Frozen input identity: every distributed input must match its recorded SHA256."""

from __future__ import annotations

from utils import paths
from utils.hashing import sha256_file

import pytest


def test_every_frozen_input_matches_recorded_sha256(expected_hashes):
    failures = []
    for relative_path, spec in sorted(expected_hashes["files"].items()):
        target = paths.PACKAGE_ROOT / relative_path
        if not target.is_file():
            failures.append(f"missing: {relative_path}")
            continue
        if target.stat().st_size != spec["size_bytes"]:
            failures.append(f"size mismatch: {relative_path}")
        if sha256_file(target) != spec["sha256"]:
            failures.append(f"sha256 mismatch: {relative_path}")
    assert not failures, failures


@pytest.mark.parametrize(
    "relative_path, expected_sha256",
    [
        (
            "data/frozen_inputs/exploration/pairwise_relations.csv",
            "34AD797084524C5FC471877B4A8B7011B54FAAECF0DA58ECCF07D9655C922920",
        ),
        (
            "data/frozen_inputs/validation/validation_correlations.csv",
            "B0A2CCCB5B42DAEED12B51CDC129F681FC05946B3C42A11065E97CC10E35E75B",
        ),
        (
            "data/frozen_inputs/validation/validation_direction_checks.csv",
            "15E31E50CAAB5F6A786209BBBB8C1249EB4AB8F39E00601038046946CEE880E3",
        ),
        (
            "data/frozen_inputs/validation/validation_summary_by_city.csv",
            "2280D081A347AC1053872A2C167940E37DA4471E2B2D3326A7734FC53AD92B1F",
        ),
        (
            "data/frozen_inputs/validation/validation_hypothesis_summary.csv",
            "9CB157A722913EBD88ED7D3103E38DBE704BCA816338613944C92D3ABCCEF7C5",
        ),
        (
            "data/frozen_inputs/synthesis/01_directional_concordance.csv",
            "6DF36B770F23A2F49445156B5F7D881AECEF6B2B48239856F96098DBAC48EFC2",
        ),
        (
            "data/frozen_inputs/synthesis/02_exploration_validation_magnitude_summary.csv",
            "648F7B5412DA4DEC94C22D41A71E0CA194444E838B54C50E447CB2E318FBD98C",
        ),
        (
            "data/frozen_inputs/synthesis/03_scale_coverage_metric_sensitivity.csv",
            "8012B2B3CAD38E4AAA19A9DA91E49F362A77BC023646AFBCE5BDC6402A0CD082",
        ),
        (
            "data/frozen_inputs/synthesis/04_relationship_robustness_profile.csv",
            "6ED93EF7528BE61924E1421E26BD77A83ECE54C3DFF4A6C41536B42AA2D7A494",
        ),
    ],
)
def test_manuscript_critical_inputs_match_published_hashes(relative_path, expected_sha256):
    target = paths.PACKAGE_ROOT / relative_path
    assert target.is_file(), f"missing frozen input: {relative_path}"
    assert sha256_file(target) == expected_sha256


def test_wp05c_method_contract_document_hash(expected_hashes):
    spec = expected_hashes["files"]["config/WP-MORPH-05C_METHOD_CONTRACT_V1.md"]
    assert spec["sha256"] == "936A3FB27990A2F1BEBFD976333E89B216086E4B9550B18B6454D8A47C2133D3"
    assert sha256_file(paths.CONFIG_DIR / "WP-MORPH-05C_METHOD_CONTRACT_V1.md") == spec["sha256"]
