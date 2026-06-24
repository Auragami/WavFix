"""Input scanning and file discovery helpers."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from .constants import ACCEPTED_EXTENSIONS
from .models import InputFileSpec


def is_supported_file(path: Path | str) -> bool:
    return Path(path).suffix.lower() in ACCEPTED_EXTENSIONS


def scan_input_specs(input_paths: Sequence[Path | str]) -> list[InputFileSpec]:
    """Expand input paths into file specs preserving selected folder roots."""
    discovered: list[InputFileSpec] = []
    seen_indices: dict[Path, int] = {}

    for raw_path in input_paths:
        selected_path = Path(raw_path).expanduser().resolve()
        if not selected_path.exists():
            continue

        if selected_path.is_file():
            if selected_path.name.startswith("._") or not is_supported_file(selected_path):
                continue
            spec = InputFileSpec(path=selected_path, source_root=None)
            if selected_path not in seen_indices:
                discovered.append(spec)
                seen_indices[selected_path] = len(discovered) - 1
            continue

        source_root = selected_path
        for root_dir, _, files in os.walk(source_root):
            for file_name in files:
                if file_name.startswith("._"):
                    continue
                candidate = (Path(root_dir) / file_name).resolve()
                if not is_supported_file(candidate):
                    continue

                spec = InputFileSpec(path=candidate, source_root=source_root)
                index = seen_indices.get(candidate)
                if index is None:
                    discovered.append(spec)
                    seen_indices[candidate] = len(discovered) - 1
                elif discovered[index].source_root is None:
                    # Prefer preserving structure if selected both directly and via folder.
                    discovered[index] = spec

    return discovered


def scan_inputs(input_paths: Sequence[Path | str]) -> list[Path]:
    """Expand input paths into a normalized list of supported files."""
    return [spec.path for spec in scan_input_specs(input_paths)]
