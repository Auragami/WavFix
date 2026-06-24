"""File inspection helpers."""

from __future__ import annotations

from pathlib import Path

from .decisions import decide_repair_action
from .metadata_chunks import unsupported_metadata_chunk_ids
from .models import (
    BitDepthPolicy,
    FileInspection,
    MetadataPolicy,
    MultiChannelPolicy,
    RepairAction,
    SampleRatePolicy,
    WavFormatKind,
    WavMetadata,
)
from .wav_parser import parse_wav_file


def inspect_wav_metadata(
    path: Path | str,
    metadata: WavMetadata,
    *,
    profile_name: str = "preserve_supported_rate",
    allow_conversion: bool = True,
    multichannel_policy: MultiChannelPolicy = "downmix",
    metadata_policy: MetadataPolicy = "best_effort",
    sample_rate_policy: SampleRatePolicy = "convert_nearest",
    bit_depth_policy: BitDepthPolicy = "convert",
) -> FileInspection:
    """Build a FileInspection from pre-parsed WAV metadata."""
    file_path = Path(path)
    ext = file_path.suffix.lower()

    if metadata.format_kind == WavFormatKind.MALFORMED:
        return FileInspection(
            path=file_path,
            extension=ext,
            format_kind=metadata.format_kind,
            action=RepairAction.REJECT,
            reason=metadata.parse_error or "Malformed WAV.",
            wav_metadata=metadata,
            color_tag="red",
            error=metadata.parse_error,
        )

    outcome = decide_repair_action(
        metadata,
        profile_name=profile_name,
        allow_conversion=allow_conversion,
        multichannel_policy=multichannel_policy,
        sample_rate_policy=sample_rate_policy,
        bit_depth_policy=bit_depth_policy,
    )

    action = outcome.action
    reason = outcome.reason
    if metadata_policy == "strict_preserve" and action == RepairAction.CONVERT:
        unsupported_chunks = unsupported_metadata_chunk_ids(metadata)
        if unsupported_chunks:
            unique = ", ".join(sorted(set(unsupported_chunks)))
            action = RepairAction.REJECT
            reason = (
                "Strict metadata preservation is enabled and this file contains "
                f"unsupported metadata chunk(s): {unique}."
            )

    if action == RepairAction.PASS_THROUGH:
        color_tag = "green"
    elif action == RepairAction.HEADER_FIX:
        color_tag = "yellow"
    elif action == RepairAction.CONVERT:
        color_tag = "orange"
    else:
        color_tag = "red"

    error = None
    if action == RepairAction.REJECT:
        error = reason

    return FileInspection(
        path=file_path,
        extension=ext,
        format_kind=metadata.format_kind,
        action=action,
        reason=reason,
        wav_metadata=metadata,
        color_tag=color_tag,
        error=error,
    )


def inspect_file(
    path: Path | str,
    *,
    profile_name: str = "preserve_supported_rate",
    allow_conversion: bool = True,
    multichannel_policy: MultiChannelPolicy = "downmix",
    metadata_policy: MetadataPolicy = "best_effort",
    sample_rate_policy: SampleRatePolicy = "convert_nearest",
    bit_depth_policy: BitDepthPolicy = "convert",
) -> FileInspection:
    """Inspect a file and return color/tag metadata used by UI and processing."""
    file_path = Path(path)
    ext = file_path.suffix.lower()

    if ext != ".wav":
        return FileInspection(
            path=file_path,
            extension=ext,
            format_kind=WavFormatKind.NON_WAV,
            action=RepairAction.PASS_THROUGH,
            reason="Non-WAV file will be copied unchanged.",
            color_tag="neutral",
        )

    metadata = parse_wav_file(file_path, include_chunks=metadata_policy == "strict_preserve")
    return inspect_wav_metadata(
        file_path,
        metadata,
        profile_name=profile_name,
        allow_conversion=allow_conversion,
        multichannel_policy=multichannel_policy,
        metadata_policy=metadata_policy,
        sample_rate_policy=sample_rate_policy,
        bit_depth_policy=bit_depth_policy,
    )


def short_status(inspection: FileInspection) -> str:
    """Return compact processing text for the treeview Process column."""
    if inspection.action is None:
        return "UNKNOWN"
    labels = {
        RepairAction.PASS_THROUGH: "Pass",
        RepairAction.HEADER_FIX: "Repair",
        RepairAction.CONVERT: "Convert",
        RepairAction.REJECT: "Skip",
    }
    return labels.get(inspection.action, "Unknown")


def format_kind_label(kind: WavFormatKind) -> str:
    """Human-readable format label for UI/CLI reporting."""
    labels = {
        WavFormatKind.NON_WAV: "Non-WAV",
        WavFormatKind.PCM: "PCM",
        WavFormatKind.IEEE_FLOAT: "Float",
        WavFormatKind.EXTENSIBLE_PCM: "Extensible PCM",
        WavFormatKind.EXTENSIBLE_FLOAT: "Extensible Float",
        WavFormatKind.EXTENSIBLE_UNSUPPORTED: "Extensible Unsupported",
        WavFormatKind.UNSUPPORTED: "Unsupported",
        WavFormatKind.MALFORMED: "Malformed",
    }
    return labels.get(kind, "Unknown")
