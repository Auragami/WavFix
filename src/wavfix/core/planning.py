"""Output path planning for smart-save behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import OutputPlanningError
from .models import InputFileSpec, OverwritePolicy


@dataclass(slots=True)
class OutputPlanContext:
    output_dir: Path
    overwrite_policy: OverwritePolicy
    existing_items: set[str]
    root_aliases: dict[Path, str] = field(default_factory=dict)


def safe_common_parent(paths: list[Path]) -> Path:
    if not paths:
        raise OutputPlanningError("Cannot determine common parent for an empty input set.")
    common_path = os.path.commonpath([str(path) for path in paths])
    common = Path(common_path)
    if common.is_file():
        return common.parent
    return common


def _insert_clean_suffix(file_name: str) -> str:
    if "." not in file_name:
        return f"{file_name}_clean"
    stem, ext = file_name.rsplit(".", 1)
    return f"{stem}_clean.{ext}"


def _next_available_name(name: str, existing_items: set[str]) -> str:
    if name not in existing_items:
        return name

    candidate = _insert_clean_suffix(name)
    if candidate not in existing_items:
        return candidate

    if "." in candidate:
        stem, ext = candidate.rsplit(".", 1)
    else:
        stem, ext = candidate, ""
    index = 2
    while True:
        if ext:
            numbered = f"{stem}_{index}.{ext}"
        else:
            numbered = f"{stem}_{index}"
        if numbered not in existing_items:
            return numbered
        index += 1


def plan_output_path(file_spec: InputFileSpec, context: OutputPlanContext) -> Path:
    """Plan output path preserving selected folder structure where applicable."""
    if file_spec.source_root is not None:
        source_root = file_spec.source_root
        alias = context.root_aliases.get(source_root)
        if alias is None:
            root_name = source_root.name
            if context.overwrite_policy == "no":
                alias = _next_available_name(root_name, context.existing_items)
            else:
                alias = root_name
            context.root_aliases[source_root] = alias
            context.existing_items.add(alias)

        relative_path = file_spec.path.relative_to(source_root)
        target = context.output_dir / alias / relative_path
        return target

    output_name = file_spec.path.name
    if context.overwrite_policy == "no":
        output_name = _next_available_name(output_name, context.existing_items)
    context.existing_items.add(output_name)
    return context.output_dir / output_name
