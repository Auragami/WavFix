"""Core file processing workflows."""

from __future__ import annotations

import importlib
import os
import shutil
import struct
import subprocess
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Semaphore
from typing import Any

from .constants import COMPATIBILITY_PROFILES, SUPPORTED_PCM_BIT_DEPTHS
from .decisions import ConversionTarget, decide_repair_action
from .metadata_chunks import is_common_metadata_chunk
from .models import (
    BitDepthPolicy,
    ConverterBackend,
    InputFileSpec,
    MetadataPolicy,
    MultiChannelPolicy,
    OverwritePolicy,
    PerformanceMode,
    ProcessRequest,
    ProcessResult,
    ProgressEvent,
    RepairAction,
    SampleRatePolicy,
    WavFormatKind,
    WavMetadata,
)
from .planning import OutputPlanContext, plan_output_path, safe_common_parent
from .wav_parser import parse_wav_file

ProgressCallback = Callable[[ProgressEvent], None] | None
OverwriteResolver = Callable[[], bool] | None


@dataclass(slots=True)
class WorkerOutcome:
    output_path: Path
    action: RepairAction
    reason: str
    warning_messages: list[str]
    error: str | None = None


@dataclass(slots=True)
class PerformanceConfig:
    worker_count: int
    conversion_slots: int
    resample_quality: str


@dataclass(slots=True)
class MetadataChunkPlan:
    chunk_id: bytes
    size: int
    data_offset: int


def resolve_performance_config(
    performance_mode: PerformanceMode,
    *,
    max_workers_override: int | None = None,
    cpu_count: int | None = None,
) -> PerformanceConfig:
    detected_cpu = max(1, cpu_count if cpu_count is not None else (os.cpu_count() or 4))
    reserved_cpu = 2 if detected_cpu >= 6 else 1
    available = max(1, detected_cpu - reserved_cpu)

    if performance_mode == "conservative":
        worker_count = max(1, min(4, detected_cpu // 2))
        conversion_slots = 1
        resample_quality = "HQ"
    elif performance_mode == "fast":
        worker_count = max(1, min(16, detected_cpu - 1))
        conversion_slots = max(1, min(4, detected_cpu // 4))
        resample_quality = "HQ"
    else:
        worker_count = max(1, min(8, available))
        conversion_slots = 2 if detected_cpu >= 6 else 1
        resample_quality = "VHQ"

    if max_workers_override is not None:
        worker_count = max(1, max_workers_override)

    return PerformanceConfig(
        worker_count=worker_count,
        conversion_slots=max(1, conversion_slots),
        resample_quality=resample_quality,
    )


def _copy_unmodified(input_file: Path, output_file: Path) -> None:
    shutil.copy2(input_file, output_file)


def _normalized_path_key(path: Path) -> str:
    return path.resolve().as_posix().casefold()


def _build_canonical_pcm_fmt(
    channels: int,
    sample_rate: int,
    bits_per_sample: int,
) -> bytes:
    block_align = channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    return struct.pack(
        "<HHIIHH",
        0x0001,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )


def _copy_stream_range(
    *,
    source,
    destination,
    size: int,
    buffer_size: int = 1024 * 1024,
) -> None:
    remaining = size
    while remaining > 0:
        chunk = source.read(min(buffer_size, remaining))
        if not chunk:
            raise ValueError("Unexpected EOF while copying WAV chunk payload.")
        destination.write(chunk)
        remaining -= len(chunk)


def _streams_equal_range(
    *,
    left_path: Path,
    left_offset: int,
    right_path: Path,
    right_offset: int,
    size: int,
    buffer_size: int = 1024 * 1024,
) -> bool:
    remaining = size
    with left_path.open("rb") as left_handle, right_path.open("rb") as right_handle:
        left_handle.seek(left_offset)
        right_handle.seek(right_offset)

        while remaining > 0:
            read_size = min(buffer_size, remaining)
            left_chunk = left_handle.read(read_size)
            right_chunk = right_handle.read(read_size)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return False
            remaining -= len(left_chunk)

    return True


def _write_header_fixed_file(
    input_file: Path,
    output_file: Path,
    *,
    metadata: WavMetadata,
) -> None:
    if metadata.format_kind != WavFormatKind.EXTENSIBLE_PCM:
        raise ValueError("Header fix is only valid for extensible PCM WAV files.")
    if not metadata.chunks:
        raise ValueError("Chunk table missing; cannot perform streaming header fix.")

    channels = metadata.channels
    sample_rate = metadata.sample_rate
    bits = metadata.bits_per_sample
    if channels is None or sample_rate is None or bits is None:
        raise ValueError("Incomplete WAV metadata; cannot build canonical PCM fmt chunk.")

    canonical_fmt = _build_canonical_pcm_fmt(channels, sample_rate, bits)

    with input_file.open("rb") as source, output_file.open("wb") as destination:
        destination.write(b"RIFF\x00\x00\x00\x00WAVE")

        for chunk in metadata.chunks:
            source.seek(chunk.offset)
            chunk_header = source.read(8)
            if len(chunk_header) != 8:
                raise ValueError("Chunk header could not be read during header fix.")
            chunk_id = chunk_header[:4]

            if chunk_id == b"fmt ":
                destination.write(chunk_id)
                destination.write(struct.pack("<I", len(canonical_fmt)))
                destination.write(canonical_fmt)
                if len(canonical_fmt) % 2:
                    destination.write(b"\x00")
                continue

            destination.write(chunk_id)
            destination.write(struct.pack("<I", chunk.size))
            source.seek(chunk.data_offset)
            _copy_stream_range(source=source, destination=destination, size=chunk.size)
            if chunk.size % 2:
                destination.write(b"\x00")

        total_size = destination.tell()
        destination.seek(4)
        destination.write(struct.pack("<I", total_size - 8))


_SPEAKER_COEFFICIENTS: dict[int, tuple[float, float]] = {
    0: (1.0, 0.0),  # FL
    1: (0.0, 1.0),  # FR
    2: (0.7071067811865476, 0.7071067811865476),  # FC (-3 dB to each side)
    3: (0.5, 0.5),  # LFE (attenuated blend)
    4: (0.7071067811865476, 0.0),  # BL
    5: (0.0, 0.7071067811865476),  # BR
    6: (0.7071067811865476, 0.0),  # FLC
    7: (0.0, 0.7071067811865476),  # FRC
    8: (0.5, 0.5),  # BC
    9: (0.7071067811865476, 0.0),  # SL
    10: (0.0, 0.7071067811865476),  # SR
    11: (0.5, 0.5),  # TC
    12: (0.7071067811865476, 0.0),  # TFL
    13: (0.5, 0.5),  # TFC
    14: (0.0, 0.7071067811865476),  # TFR
    15: (0.7071067811865476, 0.0),  # TBL
    16: (0.0, 0.7071067811865476),  # TBR
}
_DEFAULT_SPEAKER_ORDER_BITS: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 9, 10)
_CONVERSION_BLOCK_FRAMES = 65536


@lru_cache(maxsize=1)
def _load_conversion_backends() -> tuple[Any, Any, Any]:
    try:
        numpy_module = importlib.import_module("numpy")
        soundfile_module = importlib.import_module("soundfile")
        soxr_module = importlib.import_module("soxr")
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "Audio conversion backend is unavailable. Install numpy, soundfile, and soxr."
        ) from exc

    soundfile_class = getattr(soundfile_module, "SoundFile", None)
    if soundfile_class is None:
        raise RuntimeError("Audio conversion backend is unavailable: soundfile.SoundFile missing.")
    if not callable(getattr(soundfile_class, "blocks", None)):
        raise RuntimeError(
            "Audio conversion backend is unavailable: soundfile.SoundFile.blocks missing."
        )
    if not callable(getattr(soxr_module, "resample", None)):
        raise RuntimeError("Audio conversion backend is unavailable: soxr.resample missing.")
    if not hasattr(numpy_module.random, "default_rng"):
        raise RuntimeError(
            "Audio conversion backend is unavailable: numpy.random.default_rng missing."
        )
    return numpy_module, soundfile_module, soxr_module


def warm_conversion_backend() -> None:
    """Preload conversion libraries and run a tiny resampler call off the UI path."""
    try:
        np_module, _soundfile_module, soxr_module = _load_conversion_backends()
        sample = np_module.zeros((32, 1), dtype=np_module.float32)
        soxr_module.resample(sample, 48000, 44100, quality="HQ")
    except Exception:
        return


def _speaker_bits_for_layout(channel_count: int, channel_mask: int | None) -> list[int]:
    if channel_mask is not None and channel_mask > 0:
        bits = [bit for bit in range(32) if channel_mask & (1 << bit)]
        if len(bits) == channel_count:
            return bits

    if channel_count <= len(_DEFAULT_SPEAKER_ORDER_BITS):
        return list(_DEFAULT_SPEAKER_ORDER_BITS[:channel_count])

    overflow = channel_count - len(_DEFAULT_SPEAKER_ORDER_BITS)
    return [*_DEFAULT_SPEAKER_ORDER_BITS, *([-1] * overflow)]


@lru_cache(maxsize=128)
def _stereo_coefficients_for_layout(
    channel_count: int,
    channel_mask: int | None,
) -> tuple[tuple[float, ...], tuple[float, ...], float]:
    speaker_bits = _speaker_bits_for_layout(channel_count, channel_mask)
    left_coeff = [0.0] * channel_count
    right_coeff = [0.0] * channel_count
    for index, speaker_bit in enumerate(speaker_bits):
        left, right = _SPEAKER_COEFFICIENTS.get(speaker_bit, (0.5, 0.5))
        left_coeff[index] = left
        right_coeff[index] = right

    left_scale = sum(abs(value) for value in left_coeff)
    right_scale = sum(abs(value) for value in right_coeff)
    normalizer = max(1.0, left_scale, right_scale)
    return tuple(left_coeff), tuple(right_coeff), normalizer


def _downmix_to_stereo(
    np_module: Any,
    samples: Any,
    *,
    channel_mask: int | None,
) -> Any:
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)

    channel_count = int(samples.shape[1])
    if channel_count == 1:
        return np_module.repeat(samples, 2, axis=1)
    if channel_count == 2:
        return samples

    left_tuple, right_tuple, normalizer = _stereo_coefficients_for_layout(
        channel_count,
        channel_mask,
    )
    left_coeff = np_module.asarray(left_tuple, dtype=np_module.float64)
    right_coeff = np_module.asarray(right_tuple, dtype=np_module.float64)

    left = np_module.sum(samples * left_coeff.reshape((1, -1)), axis=1) / normalizer
    right = np_module.sum(samples * right_coeff.reshape((1, -1)), axis=1) / normalizer
    return np_module.stack((left, right), axis=1)


def _to_aligned_channels(
    np_module: Any,
    samples: Any,
    target_channels: int,
    *,
    channel_mask: int | None,
) -> Any:
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)

    current_channels = int(samples.shape[1])
    if current_channels == target_channels:
        return samples
    if target_channels == 1:
        return np_module.mean(samples, axis=1, keepdims=True)
    if target_channels == 2:
        return _downmix_to_stereo(np_module, samples, channel_mask=channel_mask)
    raise ValueError(f"Unsupported target channel count for conversion: {target_channels}")


def _create_soxr_resample_stream(
    soxr_module: Any,
    *,
    input_rate: int,
    output_rate: int,
    channels: int,
    quality: str,
) -> Any | None:
    stream_class = getattr(soxr_module, "ResampleStream", None)
    if stream_class is None:
        return None

    attempts: tuple[tuple[tuple[Any, ...], dict[str, Any]], ...] = (
        (
            (),
            {
                "in_rate": input_rate,
                "out_rate": output_rate,
                "num_channels": channels,
                "quality": quality,
            },
        ),
        (
            (),
            {
                "in_rate": input_rate,
                "out_rate": output_rate,
                "channels": channels,
                "quality": quality,
            },
        ),
        ((input_rate, output_rate, channels), {"quality": quality}),
        ((input_rate, output_rate, channels), {}),
    )
    for args, kwargs in attempts:
        try:
            candidate = stream_class(*args, **kwargs)
            if any(
                callable(getattr(candidate, name, None))
                for name in ("resample_chunk", "process", "resample")
            ):
                return candidate
        except Exception:
            continue
    return None


def _resample_stream_chunk(resampler: Any, block: Any, *, last: bool) -> Any:
    for method_name in ("resample_chunk", "process", "resample"):
        method = getattr(resampler, method_name, None)
        if not callable(method):
            continue
        try:
            return method(block, last=last)
        except TypeError:
            try:
                return method(block, last)
            except TypeError:
                return method(block)
    raise RuntimeError("SoXR stream resampler has no supported chunk API.")


def _resample_block(
    soxr_module: Any,
    *,
    resampler: Any | None,
    block: Any,
    input_rate: int,
    output_rate: int,
    quality: str,
    last: bool,
) -> Any:
    if input_rate == output_rate:
        return block
    if resampler is not None:
        return _resample_stream_chunk(resampler, block, last=last)
    return soxr_module.resample(block, input_rate, output_rate, quality=quality)


def _quantize_pcm_float(
    np_module: Any,
    samples: Any,
    bit_depth: int,
    *,
    rng: Any | None = None,
    apply_dither: bool = True,
) -> tuple[Any, int]:
    if bit_depth not in {16, 24}:
        raise ValueError(f"Unsupported conversion target bit depth: {bit_depth}")

    max_int = float((1 << (bit_depth - 1)) - 1)
    min_int = float(-(1 << (bit_depth - 1)))
    clipped = np_module.clip(samples, -1.0, 1.0)
    clipped_samples = int(np_module.count_nonzero(samples != clipped))

    if apply_dither:
        rng_instance = rng if rng is not None else np_module.random.default_rng()
        dither = (
            rng_instance.random(clipped.shape) + rng_instance.random(clipped.shape) - 1.0
        ) / max_int
        scaled = (clipped + dither) * max_int
    else:
        scaled = clipped * max_int

    quantized = np_module.rint(scaled)
    quantized = np_module.clip(quantized, min_int, max_int).astype(np_module.int32, copy=False)
    return quantized, clipped_samples


def _int_to_float_grid(np_module: Any, samples: Any, bit_depth: int) -> Any:
    max_int = float((1 << (bit_depth - 1)) - 1)
    return samples.astype(np_module.float32, copy=False) / max_int


def _plan_metadata_chunks(
    *,
    input_file: Path,
    metadata: WavMetadata,
    metadata_policy: MetadataPolicy,
) -> tuple[list[MetadataChunkPlan], list[str]]:
    plans: list[MetadataChunkPlan] = []

    if not metadata.chunks:
        if metadata_policy == "strict_preserve":
            raise ValueError("Strict metadata preservation requires chunk table metadata.")
        return plans, []

    with input_file.open("rb") as source:
        for chunk in metadata.chunks:
            source.seek(chunk.offset)
            header = source.read(8)
            if len(header) != 8:
                if metadata_policy == "strict_preserve":
                    raise ValueError(
                        "Strict metadata preservation failed: chunk header unreadable."
                    )
                continue

            chunk_id_bytes = header[:4]
            chunk_id = chunk_id_bytes.decode("ascii", errors="replace")
            if chunk_id in {"fmt ", "data"}:
                continue

            if not is_common_metadata_chunk(chunk_id):
                if metadata_policy == "strict_preserve":
                    raise ValueError(
                        "Strict metadata preservation rejected unsupported metadata chunk: "
                        f"{chunk_id}."
                    )
                continue

            plans.append(
                MetadataChunkPlan(
                    chunk_id=chunk_id_bytes,
                    size=chunk.size,
                    data_offset=chunk.data_offset,
                )
            )

    return plans, []


def _append_metadata_chunks(
    *,
    input_file: Path,
    output_file: Path,
    chunk_plans: list[MetadataChunkPlan],
) -> None:
    if not chunk_plans:
        return

    with input_file.open("rb") as source, output_file.open("r+b") as destination:
        destination.seek(0, os.SEEK_END)
        for plan in chunk_plans:
            destination.write(plan.chunk_id)
            destination.write(struct.pack("<I", plan.size))
            source.seek(plan.data_offset)
            _copy_stream_range(source=source, destination=destination, size=plan.size)
            if plan.size % 2:
                destination.write(b"\x00")

        total_size = destination.tell()
        destination.seek(4)
        destination.write(struct.pack("<I", total_size - 8))


def _run_conversion(
    *,
    input_file: Path,
    output_file: Path,
    target: ConversionTarget,
    input_metadata: WavMetadata,
    metadata_policy: MetadataPolicy,
    resample_quality: str,
) -> list[str]:
    chunk_plans, _ = _plan_metadata_chunks(
        input_file=input_file,
        metadata=input_metadata,
        metadata_policy=metadata_policy,
    )

    np_module, soundfile_module, soxr_module = _load_conversion_backends()
    subtype = "PCM_24" if target.bit_depth == 24 else "PCM_16"
    conversion_rng = np_module.random.default_rng()
    input_bits = int(input_metadata.bits_per_sample or target.bit_depth)
    source_kind = input_metadata.format_kind
    is_float_source = source_kind in {WavFormatKind.IEEE_FLOAT, WavFormatKind.EXTENSIBLE_FLOAT}
    source_channels = int(input_metadata.channels or target.channels)
    source_rate_hint = int(input_metadata.sample_rate or target.sample_rate)
    uses_processing_dsp = (
        source_channels != target.channels or source_rate_hint != target.sample_rate
    )
    apply_dither = is_float_source or input_bits >= target.bit_depth or uses_processing_dsp

    with soundfile_module.SoundFile(str(input_file), mode="r") as in_handle:
        source_rate = int(in_handle.samplerate)
        resampler = _create_soxr_resample_stream(
            soxr_module,
            input_rate=source_rate,
            output_rate=target.sample_rate,
            channels=target.channels,
            quality=resample_quality,
        )
        with soundfile_module.SoundFile(
            str(output_file),
            mode="w",
            samplerate=target.sample_rate,
            channels=target.channels,
            format="WAV",
            subtype=subtype,
        ) as out_handle:
            blocks = in_handle.blocks(
                blocksize=_CONVERSION_BLOCK_FRAMES,
                dtype="float64",
                always_2d=True,
            )
            for block in blocks:
                aligned = _to_aligned_channels(
                    np_module,
                    block,
                    target.channels,
                    channel_mask=input_metadata.channel_mask,
                )
                if source_rate != target.sample_rate and resampler is not None:
                    try:
                        resampled = _resample_block(
                            soxr_module,
                            resampler=resampler,
                            block=aligned,
                            input_rate=source_rate,
                            output_rate=target.sample_rate,
                            quality=resample_quality,
                            last=False,
                        )
                    except RuntimeError:
                        resampler = None
                        resampled = _resample_block(
                            soxr_module,
                            resampler=None,
                            block=aligned,
                            input_rate=source_rate,
                            output_rate=target.sample_rate,
                            quality=resample_quality,
                            last=False,
                        )
                else:
                    resampled = _resample_block(
                        soxr_module,
                        resampler=resampler,
                        block=aligned,
                        input_rate=source_rate,
                        output_rate=target.sample_rate,
                        quality=resample_quality,
                        last=False,
                    )
                if resampled is None or getattr(resampled, "size", 0) == 0:
                    continue

                quantized, _ = _quantize_pcm_float(
                    np_module,
                    resampled,
                    target.bit_depth,
                    rng=conversion_rng,
                    apply_dither=apply_dither,
                )
                out_handle.write(_int_to_float_grid(np_module, quantized, target.bit_depth))

            if source_rate != target.sample_rate and resampler is not None:
                flush_block = _resample_block(
                    soxr_module,
                    resampler=resampler,
                    block=np_module.empty((0, target.channels), dtype=np_module.float64),
                    input_rate=source_rate,
                    output_rate=target.sample_rate,
                    quality=resample_quality,
                    last=True,
                )
                if flush_block is not None and getattr(flush_block, "size", 0) > 0:
                    quantized, _ = _quantize_pcm_float(
                        np_module,
                        flush_block,
                        target.bit_depth,
                        rng=conversion_rng,
                        apply_dither=apply_dither,
                    )
                    out_handle.write(_int_to_float_grid(np_module, quantized, target.bit_depth))

    _append_metadata_chunks(
        input_file=input_file,
        output_file=output_file,
        chunk_plans=chunk_plans,
    )
    return []


def _resolve_ffmpeg_executable(ffmpeg_path: str) -> str:
    if ffmpeg_path.strip():
        candidate = Path(ffmpeg_path).expanduser()
        if candidate.is_file():
            return str(candidate)
        raise RuntimeError(f"Configured FFmpeg executable was not found: {ffmpeg_path}")

    detected = shutil.which("ffmpeg")
    if detected is None:
        raise RuntimeError(
            "FFmpeg conversion backend is selected, but ffmpeg was not found. "
            "Choose an FFmpeg executable in Settings or switch Converter to Built-in."
        )
    return detected


def _run_ffmpeg_conversion(
    *,
    input_file: Path,
    output_file: Path,
    target: ConversionTarget,
    input_metadata: WavMetadata,
    metadata_policy: MetadataPolicy,
    ffmpeg_path: str,
    resample_quality: str,
) -> list[str]:
    chunk_plans, _ = _plan_metadata_chunks(
        input_file=input_file,
        metadata=input_metadata,
        metadata_policy=metadata_policy,
    )
    if metadata_policy == "strict_preserve" and chunk_plans:
        chunk_ids = ", ".join(
            sorted({plan.chunk_id.decode("ascii", errors="replace") for plan in chunk_plans})
        )
        raise RuntimeError(
            "Strict metadata preservation cannot be guaranteed with the FFmpeg backend "
            f"for chunk(s): {chunk_ids}. Use Built-in converter or Best Effort metadata."
        )
    executable = _resolve_ffmpeg_executable(ffmpeg_path)
    subtype = "pcm_s24le" if target.bit_depth == 24 else "pcm_s16le"
    precision = "28" if resample_quality == "VHQ" else "20"
    audio_filter = f"aresample=resampler=soxr:precision={precision}:dither_method=triangular"
    command = [
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_file),
        "-map_metadata",
        "0",
        "-vn",
        "-ac",
        str(target.channels),
        "-ar",
        str(target.sample_rate),
        "-af",
        audio_filter,
        "-c:a",
        subtype,
        str(output_file),
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        if details:
            raise RuntimeError(f"FFmpeg conversion failed: {details}")
        raise RuntimeError("FFmpeg conversion failed.")
    return []


def _validate_pass_through_output(input_file: Path, output_file: Path) -> None:
    if input_file.suffix.lower() != ".wav":
        return

    output_meta = parse_wav_file(output_file, include_chunks=False)
    if output_meta.format_kind == WavFormatKind.MALFORMED:
        raise ValueError("Output validation failed: pass-through WAV is malformed.")


def _validate_header_fix_output(
    *,
    input_file: Path,
    output_file: Path,
    input_meta: WavMetadata,
) -> None:
    output_meta = parse_wav_file(output_file, include_chunks=False)

    if output_meta.format_kind != WavFormatKind.PCM or output_meta.format_tag != 0x0001:
        raise ValueError("Output validation failed: header-fixed file is not canonical PCM WAV.")

    if (
        input_meta.channels != output_meta.channels
        or input_meta.sample_rate != output_meta.sample_rate
        or input_meta.bits_per_sample != output_meta.bits_per_sample
    ):
        raise ValueError("Output validation failed: header fix changed core stream parameters.")

    if (
        input_meta.data_offset is None
        or input_meta.data_size is None
        or output_meta.data_offset is None
        or output_meta.data_size is None
    ):
        raise ValueError("Output validation failed: missing data chunk metadata.")

    if input_meta.data_size != output_meta.data_size:
        raise ValueError("Output validation failed: audio data size changed during header fix.")

    if not _streams_equal_range(
        left_path=input_file,
        left_offset=input_meta.data_offset,
        right_path=output_file,
        right_offset=output_meta.data_offset,
        size=input_meta.data_size,
    ):
        raise ValueError("Output validation failed: audio data changed during header fix.")


def _validate_conversion_output(
    *,
    output_file: Path,
    profile_name: str,
    target: ConversionTarget,
) -> None:
    profile = COMPATIBILITY_PROFILES.get(
        profile_name,
        COMPATIBILITY_PROFILES["preserve_supported_rate"],
    )
    output_meta = parse_wav_file(output_file, include_chunks=False)

    if not output_meta.riff_valid or not output_meta.wave_valid:
        raise ValueError("Output validation failed: converted file is not a valid RIFF/WAVE file.")
    if output_meta.data_offset is None or output_meta.data_size is None:
        raise ValueError("Output validation failed: converted file is missing a valid data chunk.")

    if output_meta.format_kind != WavFormatKind.PCM or output_meta.format_tag != 0x0001:
        raise ValueError("Output validation failed: converted file is not PCM WAV.")

    if output_meta.channels not in profile.allowed_channels:
        raise ValueError("Output validation failed: converted file channels are out of profile.")

    if output_meta.sample_rate not in profile.supported_sample_rates:
        raise ValueError("Output validation failed: converted file sample rate is out of profile.")

    if output_meta.bits_per_sample not in SUPPORTED_PCM_BIT_DEPTHS:
        raise ValueError("Output validation failed: converted file bit depth is unsupported.")

    if output_meta.channels != target.channels:
        raise ValueError("Output validation failed: converted file channel target mismatch.")

    if output_meta.sample_rate != target.sample_rate:
        raise ValueError("Output validation failed: converted file sample rate target mismatch.")

    if output_meta.bits_per_sample != target.bit_depth:
        raise ValueError("Output validation failed: converted file bit depth target mismatch.")


def _process_path(
    *,
    input_path: Path,
    output_path: Path,
    profile_name: str,
    allow_conversion: bool,
    multichannel_policy: MultiChannelPolicy,
    metadata_policy: MetadataPolicy,
    sample_rate_policy: SampleRatePolicy,
    bit_depth_policy: BitDepthPolicy,
    converter_backend: ConverterBackend,
    ffmpeg_path: str,
    conversion_semaphore: Semaphore | None,
    resample_quality: str,
) -> WorkerOutcome:
    suffix = input_path.suffix.lower()
    if suffix != ".wav":
        _copy_unmodified(input_path, output_path)
        _validate_pass_through_output(input_path, output_path)
        return WorkerOutcome(
            output_path=output_path,
            action=RepairAction.PASS_THROUGH,
            reason="Non-WAV file copied unchanged.",
            warning_messages=[],
        )

    metadata = parse_wav_file(input_path, include_chunks=False)
    decision = decide_repair_action(
        metadata,
        profile_name=profile_name,
        allow_conversion=allow_conversion,
        multichannel_policy=multichannel_policy,
        sample_rate_policy=sample_rate_policy,
        bit_depth_policy=bit_depth_policy,
    )

    if decision.action == RepairAction.REJECT:
        return WorkerOutcome(
            output_path=output_path,
            action=RepairAction.REJECT,
            reason=decision.reason,
            warning_messages=decision.warnings,
        )

    if decision.action == RepairAction.PASS_THROUGH:
        _copy_unmodified(input_path, output_path)
        _validate_pass_through_output(input_path, output_path)
        return WorkerOutcome(
            output_path=output_path,
            action=RepairAction.PASS_THROUGH,
            reason=decision.reason,
            warning_messages=decision.warnings,
        )

    if decision.action == RepairAction.HEADER_FIX:
        metadata = parse_wav_file(input_path, include_chunks=True)
        _write_header_fixed_file(input_path, output_path, metadata=metadata)
        _validate_header_fix_output(
            input_file=input_path,
            output_file=output_path,
            input_meta=metadata,
        )
        return WorkerOutcome(
            output_path=output_path,
            action=RepairAction.HEADER_FIX,
            reason=decision.reason,
            warning_messages=decision.warnings,
        )

    if decision.action == RepairAction.CONVERT:
        if decision.target is None:
            raise RuntimeError("Decision requested conversion without conversion target details.")
        metadata = parse_wav_file(input_path, include_chunks=True)
        if conversion_semaphore is not None:
            conversion_semaphore.acquire()
        try:
            if converter_backend == "ffmpeg":
                conversion_warnings = _run_ffmpeg_conversion(
                    input_file=input_path,
                    output_file=output_path,
                    target=decision.target,
                    input_metadata=metadata,
                    metadata_policy=metadata_policy,
                    ffmpeg_path=ffmpeg_path,
                    resample_quality=resample_quality,
                )
            else:
                conversion_warnings = _run_conversion(
                    input_file=input_path,
                    output_file=output_path,
                    target=decision.target,
                    input_metadata=metadata,
                    metadata_policy=metadata_policy,
                    resample_quality=resample_quality,
                )
        finally:
            if conversion_semaphore is not None:
                conversion_semaphore.release()
        _validate_conversion_output(
            output_file=output_path,
            profile_name=profile_name,
            target=decision.target,
        )
        return WorkerOutcome(
            output_path=output_path,
            action=RepairAction.CONVERT,
            reason=decision.reason,
            warning_messages=[*decision.warnings, *conversion_warnings],
        )

    raise RuntimeError(f"Unhandled repair action: {decision.action}")


def _process_single_file(
    *,
    input_path_str: str,
    output_path_str: str,
    in_place: bool,
    profile_name: str,
    allow_conversion: bool,
    multichannel_policy: MultiChannelPolicy,
    metadata_policy: MetadataPolicy,
    sample_rate_policy: SampleRatePolicy,
    bit_depth_policy: BitDepthPolicy,
    converter_backend: ConverterBackend,
    ffmpeg_path: str,
    conversion_semaphore: Semaphore | None,
    resample_quality: str,
) -> WorkerOutcome:
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)

    try:
        if in_place:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            try:
                result = _process_path(
                    input_path=input_path,
                    output_path=temp_path,
                    profile_name=profile_name,
                    allow_conversion=allow_conversion,
                    multichannel_policy=multichannel_policy,
                    metadata_policy=metadata_policy,
                    sample_rate_policy=sample_rate_policy,
                    bit_depth_policy=bit_depth_policy,
                    converter_backend=converter_backend,
                    ffmpeg_path=ffmpeg_path,
                    conversion_semaphore=conversion_semaphore,
                    resample_quality=resample_quality,
                )
                if result.action != RepairAction.REJECT:
                    shutil.move(str(temp_path), str(output_path))
                return WorkerOutcome(
                    output_path=output_path,
                    action=result.action,
                    reason=result.reason,
                    warning_messages=result.warning_messages,
                )
            finally:
                if temp_path.exists():
                    temp_path.unlink()

        return _process_path(
            input_path=input_path,
            output_path=output_path,
            profile_name=profile_name,
            allow_conversion=allow_conversion,
            multichannel_policy=multichannel_policy,
            metadata_policy=metadata_policy,
            sample_rate_policy=sample_rate_policy,
            bit_depth_policy=bit_depth_policy,
            converter_backend=converter_backend,
            ffmpeg_path=ffmpeg_path,
            conversion_semaphore=conversion_semaphore,
            resample_quality=resample_quality,
        )
    except Exception as exc:  # pragma: no cover - propagated into result/errors
        return WorkerOutcome(
            output_path=output_path,
            action=RepairAction.REJECT,
            reason="Processing failed.",
            warning_messages=[],
            error=str(exc),
        )


def _resolve_overwrite_policy(
    request: ProcessRequest,
    existing_items: set[str],
    input_specs: list[InputFileSpec],
    overwrite_resolver: OverwriteResolver,
) -> OverwritePolicy:
    policy = request.overwrite_policy
    if policy != "ask":
        return policy

    has_conflict = any(
        (spec.source_root.name if spec.source_root is not None else spec.path.name)
        in existing_items
        for spec in input_specs
    )

    if not has_conflict:
        return "yes"

    if overwrite_resolver is None:
        return "no"
    return "yes" if overwrite_resolver() else "no"


def process_request(
    request: ProcessRequest,
    progress_callback: ProgressCallback = None,
    overwrite_resolver: OverwriteResolver = None,
    max_workers: int | None = None,
) -> ProcessResult:
    """Process selected files using thread-based workers with format-safe decisions."""
    if not request.input_paths and not request.input_specs:
        return ProcessResult(total=0, modified=0, copied=0)

    output_dir = request.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if request.input_specs:
        input_specs = [
            InputFileSpec(
                path=Path(spec.path).expanduser().resolve(),
                source_root=(
                    Path(spec.source_root).expanduser().resolve()
                    if spec.source_root is not None
                    else None
                ),
            )
            for spec in request.input_specs
        ]
    else:
        normalized_inputs = [Path(path).expanduser().resolve() for path in request.input_paths]
        if request.batch_mode:
            source_root = safe_common_parent(normalized_inputs)
            input_specs = [
                InputFileSpec(path=path, source_root=source_root) for path in normalized_inputs
            ]
        else:
            input_specs = [InputFileSpec(path=path, source_root=None) for path in normalized_inputs]

    existing_items = set(os.listdir(output_dir)) if output_dir.exists() else set()

    overwrite_policy = _resolve_overwrite_policy(
        request,
        existing_items,
        input_specs,
        overwrite_resolver,
    )

    context = OutputPlanContext(
        output_dir=output_dir,
        overwrite_policy=overwrite_policy,
        existing_items=existing_items,
    )

    input_path_keys = {spec.path: _normalized_path_key(spec.path) for spec in input_specs}
    tasks: list[tuple[Path, Path, bool]] = []
    created_dirs: set[Path] = set()
    for file_spec in input_specs:
        output_path = plan_output_path(file_spec, context)
        output_parent = output_path.parent
        if output_parent not in created_dirs:
            output_parent.mkdir(parents=True, exist_ok=True)
            created_dirs.add(output_parent)
        in_place = input_path_keys[file_spec.path] == _normalized_path_key(output_path)
        tasks.append((file_spec.path, output_path, in_place))

    performance_config = resolve_performance_config(
        request.performance_mode,
        max_workers_override=max_workers,
    )
    workers = performance_config.worker_count
    conversion_semaphore = Semaphore(performance_config.conversion_slots)

    modified = 0
    copied = 0
    errors: list[str] = []
    outputs: list[Path] = []

    unchanged = 0
    header_fixed = 0
    converted = 0
    rejected = 0
    warnings: list[str] = []
    unchanged_files: list[Path] = []
    header_fixed_files: list[Path] = []
    converted_files: list[Path] = []
    rejected_files: list[Path] = []

    def _emit(event: ProgressEvent) -> None:
        if progress_callback:
            progress_callback(event)

    def _collect_result(outcome: WorkerOutcome) -> None:
        nonlocal modified, copied, unchanged, header_fixed, converted, rejected

        if outcome.error is not None:
            message = f"{outcome.output_path}: {outcome.error}"
            errors.append(message)
            rejected += 1
            rejected_files.append(outcome.output_path)
            _emit(
                ProgressEvent(
                    kind="error",
                    message=f"Error while processing file: {outcome.output_path} ({outcome.error})",
                    path=outcome.output_path,
                )
            )
            return

        for warning in outcome.warning_messages:
            warning_message = f"{outcome.output_path}: {warning}"
            warnings.append(warning_message)
            _emit(
                ProgressEvent(
                    kind="warning",
                    message=f"Warning: {warning_message}",
                    path=outcome.output_path,
                )
            )

        if outcome.action == RepairAction.REJECT:
            rejected += 1
            rejected_files.append(outcome.output_path)
            warnings.append(f"{outcome.output_path}: rejected - {outcome.reason}")
            _emit(
                ProgressEvent(
                    kind="reject",
                    message=f"Rejected: {outcome.output_path} ({outcome.reason})",
                    path=outcome.output_path,
                )
            )
            return

        outputs.append(outcome.output_path)

        if outcome.action == RepairAction.PASS_THROUGH:
            unchanged += 1
            unchanged_files.append(outcome.output_path)
            copied += 1
            _emit(
                ProgressEvent(
                    kind="file",
                    message=f"Unchanged copy: {outcome.output_path}",
                    path=outcome.output_path,
                )
            )
            return

        if outcome.action == RepairAction.HEADER_FIX:
            header_fixed += 1
            header_fixed_files.append(outcome.output_path)
            modified += 1
            _emit(
                ProgressEvent(
                    kind="file",
                    message=f"Header fixed: {outcome.output_path}",
                    path=outcome.output_path,
                )
            )
            return

        if outcome.action == RepairAction.CONVERT:
            converted += 1
            converted_files.append(outcome.output_path)
            modified += 1
            _emit(
                ProgressEvent(
                    kind="file",
                    message=f"Converted: {outcome.output_path}",
                    path=outcome.output_path,
                )
            )
            return

        errors.append(f"{outcome.output_path}: unhandled action {outcome.action}")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _process_single_file,
                input_path_str=str(input_path),
                output_path_str=str(output_path),
                in_place=in_place,
                profile_name=request.profile,
                allow_conversion=request.allow_conversion,
                multichannel_policy=request.multichannel_policy,
                metadata_policy=request.metadata_policy,
                sample_rate_policy=request.sample_rate_policy,
                bit_depth_policy=request.bit_depth_policy,
                converter_backend=request.converter_backend,
                ffmpeg_path=request.ffmpeg_path,
                conversion_semaphore=conversion_semaphore,
                resample_quality=performance_config.resample_quality,
            )
            for input_path, output_path, in_place in tasks
        ]

        for future in as_completed(futures):
            _collect_result(future.result())

    result = ProcessResult(
        total=len(tasks),
        modified=modified,
        copied=copied,
        errors=errors,
        outputs=outputs,
        unchanged=unchanged,
        header_fixed=header_fixed,
        converted=converted,
        rejected=rejected,
        warnings=warnings,
        unchanged_files=unchanged_files,
        header_fixed_files=header_fixed_files,
        converted_files=converted_files,
        rejected_files=rejected_files,
    )

    _emit(ProgressEvent(kind="done", message="Done!"))

    return result
