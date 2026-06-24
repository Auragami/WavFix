"""Lightweight GitHub release update checks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/Dreamwalkertunes/WavFix/releases/latest"


@dataclass(slots=True)
class UpdateInfo:
    version: str
    title: str
    release_url: str
    notes: str


def normalize_version(version: str) -> str:
    """Return a comparable semantic-version-ish string."""
    match = re.search(r"\d+(?:\.\d+){0,3}", version)
    return match.group(0) if match else version.strip().lstrip("vV")


def version_tuple(version: str) -> tuple[int, ...]:
    """Convert a version string to a tuple for simple release comparisons."""
    normalized = normalize_version(version)
    parts: list[int] = []
    for item in normalized.split("."):
        try:
            parts.append(int(item))
        except ValueError:
            break
    return tuple(parts)


def is_newer_version(candidate: str, current: str) -> bool:
    """Return True when candidate is newer than current."""
    candidate_parts = version_tuple(candidate)
    current_parts = version_tuple(current)
    width = max(len(candidate_parts), len(current_parts), 1)
    padded_candidate = candidate_parts + ((0,) * (width - len(candidate_parts)))
    padded_current = current_parts + ((0,) * (width - len(current_parts)))
    return padded_candidate > padded_current


def fetch_latest_release(timeout: float = 5.0) -> UpdateInfo:
    """Fetch latest public GitHub release metadata."""
    request = Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "WavFix-Update-Checker",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not check for updates: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Could not check for updates: unexpected GitHub response.")

    return _update_info_from_payload(payload)


def _update_info_from_payload(payload: dict[str, Any]) -> UpdateInfo:
    tag_name = str(payload.get("tag_name") or payload.get("name") or "").strip()
    if not tag_name:
        raise RuntimeError("Could not check for updates: latest release has no version tag.")
    title = str(payload.get("name") or tag_name).strip()
    release_url = str(payload.get("html_url") or "").strip()
    notes = str(payload.get("body") or "").strip()
    return UpdateInfo(
        version=normalize_version(tag_name),
        title=title,
        release_url=release_url or "https://github.com/Dreamwalkertunes/WavFix/releases",
        notes=notes,
    )
