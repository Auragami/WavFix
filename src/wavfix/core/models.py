"""Data contracts for WavFix core services."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal

OverwritePolicy = Literal["ask", "yes", "no"]
ProfileName = Literal["preserve_supported_rate", "universal_pioneer_safe"]
MultiChannelPolicy = Literal["reject", "downmix"]
MetadataPolicy = Literal["best_effort", "strict_preserve"]
PerformanceMode = Literal["conservative", "balanced", "fast"]
SampleRatePolicy = Literal["convert_nearest", "reject_unsupported"]
BitDepthPolicy = Literal["convert", "reject_unsupported"]
ConverterBackend = Literal["builtin", "ffmpeg"]


class RepairAction(StrEnum):
    PASS_THROUGH = "PASS_THROUGH"
    HEADER_FIX = "HEADER_FIX"
    CONVERT = "CONVERT"
    REJECT = "REJECT"


class WavFormatKind(StrEnum):
    NON_WAV = "non_wav"
    PCM = "pcm"
    IEEE_FLOAT = "ieee_float"
    EXTENSIBLE_PCM = "extensible_pcm"
    EXTENSIBLE_FLOAT = "extensible_float"
    EXTENSIBLE_UNSUPPORTED = "extensible_unsupported"
    UNSUPPORTED = "unsupported"
    MALFORMED = "malformed"


@dataclass(slots=True)
class WavChunk:
    chunk_id: str
    offset: int
    size: int
    data_offset: int
    padded_size: int


@dataclass(slots=True)
class WavMetadata:
    path: Path
    riff_valid: bool
    wave_valid: bool
    riff_size: int | None = None
    fmt_offset: int | None = None
    fmt_size: int | None = None
    data_offset: int | None = None
    data_size: int | None = None
    format_tag: int | None = None
    format_kind: WavFormatKind = WavFormatKind.NON_WAV
    subtype_guid: bytes | None = None
    channels: int | None = None
    sample_rate: int | None = None
    bits_per_sample: int | None = None
    valid_bits_per_sample: int | None = None
    block_align: int | None = None
    channel_mask: int | None = None
    byte_rate: int | None = None
    parse_error: str | None = None
    chunks: list[WavChunk] = field(default_factory=list)


@dataclass(slots=True)
class InputFileSpec:
    path: Path
    source_root: Path | None = None


@dataclass(slots=True)
class ProcessRequest:
    output_dir: Path
    input_paths: list[Path] = field(default_factory=list)
    batch_mode: bool = False
    overwrite_policy: OverwritePolicy = "ask"
    input_specs: list[InputFileSpec] = field(default_factory=list)
    profile: ProfileName = "preserve_supported_rate"
    performance_mode: PerformanceMode = "balanced"
    allow_conversion: bool = False
    multichannel_policy: MultiChannelPolicy = "downmix"
    metadata_policy: MetadataPolicy = "best_effort"
    sample_rate_policy: SampleRatePolicy = "convert_nearest"
    bit_depth_policy: BitDepthPolicy = "convert"
    converter_backend: ConverterBackend = "builtin"
    ffmpeg_path: str = ""


@dataclass(slots=True)
class ProcessResult:
    total: int
    modified: int
    copied: int
    errors: list[str] = field(default_factory=list)
    outputs: list[Path] = field(default_factory=list)
    unchanged: int = 0
    header_fixed: int = 0
    converted: int = 0
    rejected: int = 0
    warnings: list[str] = field(default_factory=list)
    unchanged_files: list[Path] = field(default_factory=list)
    header_fixed_files: list[Path] = field(default_factory=list)
    converted_files: list[Path] = field(default_factory=list)
    rejected_files: list[Path] = field(default_factory=list)


@dataclass(slots=True)
class ProgressEvent:
    kind: str
    message: str
    path: Path | None = None


@dataclass(slots=True)
class FileInspection:
    path: Path
    extension: str
    format_kind: WavFormatKind
    action: RepairAction | None
    reason: str
    color_tag: str
    wav_metadata: WavMetadata | None = None
    error: str | None = None
