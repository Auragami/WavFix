from __future__ import annotations

from wavfix.core.update_checker import is_newer_version, normalize_version, version_tuple


def test_normalize_version_handles_release_tags() -> None:
    assert normalize_version("v2.0.1") == "2.0.1"
    assert normalize_version("WavFix 2.1.0") == "2.1.0"


def test_version_tuple_uses_numeric_parts() -> None:
    assert version_tuple("2.0.10") == (2, 0, 10)


def test_is_newer_version_compares_semver_like_tags() -> None:
    assert is_newer_version("v2.0.1", "2.0.0") is True
    assert is_newer_version("2.0.0", "2.0.0") is False
    assert is_newer_version("1.9.9", "2.0.0") is False
