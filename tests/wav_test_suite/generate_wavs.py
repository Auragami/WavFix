"""Generate deterministic WAV fixtures for parser/decision/processing tests.

Outputs:
- tests/wav_test_suite/wavs/**.wav
- tests/wav_test_suite/manifest.json
"""

from __future__ import annotations

import json
import math
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
WAVS_DIR = BASE_DIR / "wavs"
MANIFEST_PATH = BASE_DIR / "manifest.json"

PCM_GUID = bytes.fromhex("0100000000001000800000aa00389b71")
FLOAT_GUID = bytes.fromhex("0300000000001000800000aa00389b71")
UNSUPPORTED_GUID = bytes.fromhex("9900000000001000800000aa00389b71")


@dataclass(frozen=True, slots=True)
class CaseMeta:
    rel_path: str
    description: str
    expected_action: str
    expected_format_kind: str
    family: str
    channels: int | None
    sample_rate: int | None
    bits_per_sample: int | None
    format_tag: str | None
    subtype: str | None


def sine_frames(
    *,
    num_frames: int,
    channels: int,
    sample_rate: int,
    freq: float = 440.0,
) -> list[list[float]]:
    frames: list[list[float]] = []
    for index in range(num_frames):
        t = index / sample_rate
        base = 0.35 * math.sin(2.0 * math.pi * freq * t)
        frame = [base if ch % 2 == 0 else base * 0.9 for ch in range(channels)]
        frames.append(frame)
    return frames


def pack_pcm(frames: list[list[float]], bits: int) -> bytes:
    output = bytearray()
    if bits == 16:
        scale = 32767
        for frame in frames:
            for sample in frame:
                sample_i = max(-32768, min(32767, int(sample * scale)))
                output += struct.pack("<h", sample_i)
        return bytes(output)

    if bits == 24:
        scale = 8388607
        for frame in frames:
            for sample in frame:
                sample_i = max(-8388608, min(8388607, int(sample * scale)))
                if sample_i < 0:
                    sample_i += 1 << 24
                output += bytes([sample_i & 0xFF, (sample_i >> 8) & 0xFF, (sample_i >> 16) & 0xFF])
        return bytes(output)

    if bits == 32:
        scale = 2147483647
        for frame in frames:
            for sample in frame:
                sample_i = max(-(1 << 31), min((1 << 31) - 1, int(sample * scale)))
                output += struct.pack("<i", sample_i)
        return bytes(output)

    raise ValueError(f"Unsupported PCM bit depth: {bits}")


def pack_float32(frames: list[list[float]]) -> bytes:
    output = bytearray()
    for frame in frames:
        for sample in frame:
            output += struct.pack("<f", float(sample))
    return bytes(output)


def riff_chunk(chunk_id: bytes, payload: bytes) -> bytes:
    chunk = chunk_id + struct.pack("<I", len(payload)) + payload
    if len(payload) % 2:
        chunk += b"\x00"
    return chunk


def write_riff_wave(path: Path, chunks: list[bytes]) -> None:
    body = b"WAVE" + b"".join(chunks)
    riff = b"RIFF" + struct.pack("<I", len(body)) + body
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(riff)


def fmt_pcm(*, channels: int, sample_rate: int, bits: int) -> bytes:
    block_align = channels * bits // 8
    byte_rate = sample_rate * block_align
    payload = struct.pack("<HHIIHH", 0x0001, channels, sample_rate, byte_rate, block_align, bits)
    return riff_chunk(b"fmt ", payload)


def fmt_float(*, channels: int, sample_rate: int) -> bytes:
    block_align = channels * 4
    byte_rate = sample_rate * block_align
    payload = struct.pack("<HHIIHH", 0x0003, channels, sample_rate, byte_rate, block_align, 32)
    return riff_chunk(b"fmt ", payload)


def fmt_extensible(
    *,
    channels: int,
    sample_rate: int,
    bits: int,
    channel_mask: int,
    subtype_guid: bytes,
) -> bytes:
    block_align = channels * bits // 8
    byte_rate = sample_rate * block_align
    payload = struct.pack(
        "<HHIIHHH",
        0xFFFE,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        22,
    )
    payload += struct.pack("<HI", bits, channel_mask)
    payload += subtype_guid
    return riff_chunk(b"fmt ", payload)


def data_chunk(payload: bytes) -> bytes:
    return riff_chunk(b"data", payload)


def junk_chunk(size: int = 33) -> bytes:
    return riff_chunk(b"JUNK", b"\x00" * size)


def list_chunk() -> bytes:
    payload = b"INFO" + b"INAM" + struct.pack("<I", 8) + b"WavFixTS"
    return riff_chunk(b"LIST", payload)


def bext_chunk() -> bytes:
    payload = b"WavFix test suite".ljust(64, b"\x00")
    return riff_chunk(b"bext", payload)


def write_case(
    *,
    meta: CaseMeta,
    fmt: bytes,
    audio_payload: bytes,
    pre_chunks: list[bytes] | None = None,
    post_chunks: list[bytes] | None = None,
    manifest: list[dict[str, Any]],
) -> None:
    target = WAVS_DIR / meta.rel_path
    chunks = []
    if pre_chunks:
        chunks.extend(pre_chunks)
    chunks.append(fmt)
    if post_chunks:
        chunks.extend(post_chunks)
    chunks.append(data_chunk(audio_payload))
    write_riff_wave(target, chunks)

    manifest.append(
        {
            "filename": target.name,
            "path": str(target.relative_to(BASE_DIR)),
            "description": meta.description,
            "expected_action": meta.expected_action,
            "expected_format_kind": meta.expected_format_kind,
            "family": meta.family,
            "channels": meta.channels,
            "sample_rate": meta.sample_rate,
            "bits_per_sample": meta.bits_per_sample,
            "format_tag": meta.format_tag,
            "subtype": meta.subtype,
            "size_bytes": target.stat().st_size,
        }
    )


def write_malformed_cases(manifest: list[dict[str, Any]]) -> None:
    # Missing fmt chunk.
    missing_fmt = WAVS_DIR / "malformed/malformed_missing_fmt.wav"
    write_riff_wave(missing_fmt, [data_chunk(b"\x00" * 128)])
    manifest.append(
        {
            "filename": missing_fmt.name,
            "path": str(missing_fmt.relative_to(BASE_DIR)),
            "description": "Malformed WAV missing fmt chunk.",
            "expected_action": "SHOULD_REJECT",
            "expected_format_kind": "malformed",
            "family": "malformed",
            "channels": None,
            "sample_rate": None,
            "bits_per_sample": None,
            "format_tag": None,
            "subtype": None,
            "size_bytes": missing_fmt.stat().st_size,
        }
    )

    # Truncated fmt chunk payload.
    truncated = WAVS_DIR / "malformed/malformed_truncated_chunk.wav"
    payload = b"WAVE" + b"fmt " + struct.pack("<I", 40) + b"\x01\x00"
    riff = b"RIFF" + struct.pack("<I", len(payload)) + payload
    truncated.parent.mkdir(parents=True, exist_ok=True)
    truncated.write_bytes(riff)
    manifest.append(
        {
            "filename": truncated.name,
            "path": str(truncated.relative_to(BASE_DIR)),
            "description": "Malformed WAV with truncated fmt chunk.",
            "expected_action": "SHOULD_REJECT",
            "expected_format_kind": "malformed",
            "family": "malformed",
            "channels": None,
            "sample_rate": None,
            "bits_per_sample": None,
            "format_tag": None,
            "subtype": None,
            "size_bytes": truncated.stat().st_size,
        }
    )


def generate() -> list[dict[str, Any]]:
    if WAVS_DIR.exists():
        shutil.rmtree(WAVS_DIR)
    WAVS_DIR.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []

    # PCM canonical variants.
    for sample_rate, bits in [
        (44100, 16),
        (44100, 24),
        (48000, 16),
        (48000, 24),
        (96000, 16),
        (96000, 24),
    ]:
        channels = 2
        frames = sine_frames(num_frames=sample_rate, channels=channels, sample_rate=sample_rate)
        write_case(
            meta=CaseMeta(
                rel_path=f"pcm/pcm_stereo_{sample_rate}_{bits}.wav",
                description="Canonical PCM stereo WAV.",
                expected_action="SHOULD_PASS",
                expected_format_kind="pcm",
                family="pcm",
                channels=channels,
                sample_rate=sample_rate,
                bits_per_sample=bits,
                format_tag="0x0001",
                subtype=None,
            ),
            fmt=fmt_pcm(channels=channels, sample_rate=sample_rate, bits=bits),
            audio_payload=pack_pcm(frames, bits),
            manifest=manifest,
        )

    # Mono and multichannel PCM.
    for channels, name in [(1, "mono"), (4, "quad"), (6, "5_1"), (8, "7_1")]:
        sample_rate = 48000
        bits = 24
        frames = sine_frames(num_frames=sample_rate, channels=channels, sample_rate=sample_rate)
        write_case(
            meta=CaseMeta(
                rel_path=f"pcm/pcm_{name}_48000_24.wav",
                description=f"Plain PCM {name} WAV.",
                expected_action="REQUIRES_CONVERSION_OR_REJECT" if channels > 2 else "SHOULD_PASS",
                expected_format_kind="pcm",
                family="pcm",
                channels=channels,
                sample_rate=sample_rate,
                bits_per_sample=bits,
                format_tag="0x0001",
                subtype=None,
            ),
            fmt=fmt_pcm(channels=channels, sample_rate=sample_rate, bits=bits),
            audio_payload=pack_pcm(frames, bits),
            manifest=manifest,
        )

    # Float family.
    for channels, sample_rate, suffix in [
        (2, 44100, "float32_stereo_44100.wav"),
        (1, 44100, "float32_mono_44100.wav"),
        (6, 48000, "float32_5_1_48000.wav"),
    ]:
        frames = sine_frames(num_frames=sample_rate, channels=channels, sample_rate=sample_rate)
        write_case(
            meta=CaseMeta(
                rel_path=f"f32/{suffix}",
                description="IEEE float WAV; must never be relabeled as PCM.",
                expected_action=(
                    "REQUIRES_CONVERSION_OR_REJECT" if channels > 2 else "REQUIRES_CONVERSION"
                ),
                expected_format_kind="ieee_float",
                family="float",
                channels=channels,
                sample_rate=sample_rate,
                bits_per_sample=32,
                format_tag="0x0003",
                subtype=None,
            ),
            fmt=fmt_float(channels=channels, sample_rate=sample_rate),
            audio_payload=pack_float32(frames),
            manifest=manifest,
        )

    # Extensible PCM/float families.
    ext_cases = [
        (
            2,
            44100,
            24,
            0x3,
            PCM_GUID,
            "extensible_pcm_stereo_44100_24.wav",
            "SAFE_HEADER_FIX",
            "extensible_pcm",
            "PCM",
        ),
        (
            2,
            48000,
            16,
            0x3,
            PCM_GUID,
            "extensible_pcm_stereo_48000_16.wav",
            "SAFE_HEADER_FIX",
            "extensible_pcm",
            "PCM",
        ),
        (
            6,
            48000,
            24,
            0x3F,
            PCM_GUID,
            "extensible_pcm_5_1_48000_24.wav",
            "REQUIRES_CONVERSION_OR_REJECT",
            "extensible_pcm",
            "PCM",
        ),
        (
            8,
            48000,
            24,
            0x63F,
            PCM_GUID,
            "extensible_pcm_7_1_48000_24.wav",
            "REQUIRES_CONVERSION_OR_REJECT",
            "extensible_pcm",
            "PCM",
        ),
        (
            2,
            44100,
            32,
            0x3,
            FLOAT_GUID,
            "extensible_float_stereo_44100.wav",
            "REQUIRES_CONVERSION",
            "extensible_float",
            "FLOAT",
        ),
        (
            6,
            48000,
            32,
            0x3F,
            FLOAT_GUID,
            "extensible_float_5_1_48000.wav",
            "REQUIRES_CONVERSION_OR_REJECT",
            "extensible_float",
            "FLOAT",
        ),
    ]
    for channels, sample_rate, bits, mask, guid, name, expected, family, subtype in ext_cases:
        frames = sine_frames(num_frames=sample_rate, channels=channels, sample_rate=sample_rate)
        audio_payload = pack_float32(frames) if guid == FLOAT_GUID else pack_pcm(frames, bits)
        write_case(
            meta=CaseMeta(
                rel_path=f"ext/{name}",
                description=f"WAVE_FORMAT_EXTENSIBLE with {subtype.lower()} subtype.",
                expected_action=expected,
                expected_format_kind="extensible_float" if guid == FLOAT_GUID else "extensible_pcm",
                family=family,
                channels=channels,
                sample_rate=sample_rate,
                bits_per_sample=bits,
                format_tag="0xFFFE",
                subtype=subtype,
            ),
            fmt=fmt_extensible(
                channels=channels,
                sample_rate=sample_rate,
                bits=bits,
                channel_mask=mask,
                subtype_guid=guid,
            ),
            audio_payload=audio_payload,
            manifest=manifest,
        )

    # Unsupported extensible subtype.
    frames = sine_frames(num_frames=44100, channels=2, sample_rate=44100)
    write_case(
        meta=CaseMeta(
            rel_path="ext/extensible_unsupported_stereo_44100.wav",
            description="WAVE_FORMAT_EXTENSIBLE with unsupported subtype GUID.",
            expected_action="SHOULD_REJECT",
            expected_format_kind="extensible_unsupported",
            family="extensible_unsupported",
            channels=2,
            sample_rate=44100,
            bits_per_sample=24,
            format_tag="0xFFFE",
            subtype="UNSUPPORTED",
        ),
        fmt=fmt_extensible(
            channels=2,
            sample_rate=44100,
            bits=24,
            channel_mask=0x3,
            subtype_guid=UNSUPPORTED_GUID,
        ),
        audio_payload=pack_pcm(frames, 24),
        manifest=manifest,
    )

    # Layout edge cases.
    frames_pcm = sine_frames(num_frames=44100, channels=2, sample_rate=44100)
    frames_float = sine_frames(num_frames=44100, channels=2, sample_rate=44100)

    write_case(
        meta=CaseMeta(
            rel_path="pcm/pcm_with_junk_before_fmt.wav",
            description="Valid PCM WAV with JUNK chunk before fmt.",
            expected_action="SHOULD_PASS",
            expected_format_kind="pcm",
            family="pcm_layout",
            channels=2,
            sample_rate=44100,
            bits_per_sample=24,
            format_tag="0x0001",
            subtype=None,
        ),
        fmt=fmt_pcm(channels=2, sample_rate=44100, bits=24),
        audio_payload=pack_pcm(frames_pcm, 24),
        pre_chunks=[junk_chunk(33)],
        manifest=manifest,
    )

    write_case(
        meta=CaseMeta(
            rel_path="pcm/pcm_with_list_and_bext.wav",
            description="Valid PCM WAV with LIST and bext metadata chunks.",
            expected_action="SHOULD_PASS",
            expected_format_kind="pcm",
            family="pcm_layout",
            channels=2,
            sample_rate=44100,
            bits_per_sample=24,
            format_tag="0x0001",
            subtype=None,
        ),
        fmt=fmt_pcm(channels=2, sample_rate=44100, bits=24),
        audio_payload=pack_pcm(frames_pcm, 24),
        post_chunks=[list_chunk(), bext_chunk()],
        manifest=manifest,
    )

    write_case(
        meta=CaseMeta(
            rel_path="ext/extensible_pcm_with_junk.wav",
            description="Extensible PCM WAV with extra JUNK chunk.",
            expected_action="SAFE_HEADER_FIX",
            expected_format_kind="extensible_pcm",
            family="extensible_pcm_layout",
            channels=2,
            sample_rate=44100,
            bits_per_sample=24,
            format_tag="0xFFFE",
            subtype="PCM",
        ),
        fmt=fmt_extensible(
            channels=2,
            sample_rate=44100,
            bits=24,
            channel_mask=0x3,
            subtype_guid=PCM_GUID,
        ),
        audio_payload=pack_pcm(frames_pcm, 24),
        pre_chunks=[junk_chunk(37)],
        manifest=manifest,
    )

    write_case(
        meta=CaseMeta(
            rel_path="f32/float32_with_junk.wav",
            description="Float WAV with extra JUNK chunk.",
            expected_action="REQUIRES_CONVERSION",
            expected_format_kind="ieee_float",
            family="float_layout",
            channels=2,
            sample_rate=44100,
            bits_per_sample=32,
            format_tag="0x0003",
            subtype=None,
        ),
        fmt=fmt_float(channels=2, sample_rate=44100),
        audio_payload=pack_float32(frames_float),
        pre_chunks=[junk_chunk(37)],
        manifest=manifest,
    )

    # Long and tiny files.
    long_frames = sine_frames(num_frames=132300, channels=2, sample_rate=44100)
    write_case(
        meta=CaseMeta(
            rel_path="pcm/pcm_stereo_44100_24_long.wav",
            description="Longer file for size/path handling.",
            expected_action="SHOULD_PASS",
            expected_format_kind="pcm",
            family="pcm_long",
            channels=2,
            sample_rate=44100,
            bits_per_sample=24,
            format_tag="0x0001",
            subtype=None,
        ),
        fmt=fmt_pcm(channels=2, sample_rate=44100, bits=24),
        audio_payload=pack_pcm(long_frames, 24),
        manifest=manifest,
    )
    write_case(
        meta=CaseMeta(
            rel_path="ext/extensible_pcm_stereo_44100_24_long.wav",
            description="Longer file for size/path handling.",
            expected_action="SAFE_HEADER_FIX",
            expected_format_kind="extensible_pcm",
            family="ext_long",
            channels=2,
            sample_rate=44100,
            bits_per_sample=24,
            format_tag="0xFFFE",
            subtype="PCM",
        ),
        fmt=fmt_extensible(
            channels=2,
            sample_rate=44100,
            bits=24,
            channel_mask=0x3,
            subtype_guid=PCM_GUID,
        ),
        audio_payload=pack_pcm(long_frames, 24),
        manifest=manifest,
    )
    write_case(
        meta=CaseMeta(
            rel_path="f32/float32_stereo_44100_long.wav",
            description="Longer file for size/path handling.",
            expected_action="REQUIRES_CONVERSION",
            expected_format_kind="ieee_float",
            family="float_long",
            channels=2,
            sample_rate=44100,
            bits_per_sample=32,
            format_tag="0x0003",
            subtype=None,
        ),
        fmt=fmt_float(channels=2, sample_rate=44100),
        audio_payload=pack_float32(long_frames),
        manifest=manifest,
    )

    tiny_frames = sine_frames(num_frames=2205, channels=2, sample_rate=44100)
    write_case(
        meta=CaseMeta(
            rel_path="pcm/pcm_tiny.wav",
            description="Very short file.",
            expected_action="SHOULD_PASS",
            expected_format_kind="pcm",
            family="tiny",
            channels=2,
            sample_rate=44100,
            bits_per_sample=16,
            format_tag="0x0001",
            subtype=None,
        ),
        fmt=fmt_pcm(channels=2, sample_rate=44100, bits=16),
        audio_payload=pack_pcm(tiny_frames, 16),
        manifest=manifest,
    )
    write_case(
        meta=CaseMeta(
            rel_path="ext/extensible_pcm_tiny.wav",
            description="Very short file.",
            expected_action="SAFE_HEADER_FIX",
            expected_format_kind="extensible_pcm",
            family="tiny",
            channels=2,
            sample_rate=44100,
            bits_per_sample=24,
            format_tag="0xFFFE",
            subtype="PCM",
        ),
        fmt=fmt_extensible(
            channels=2,
            sample_rate=44100,
            bits=24,
            channel_mask=0x3,
            subtype_guid=PCM_GUID,
        ),
        audio_payload=pack_pcm(tiny_frames, 24),
        manifest=manifest,
    )
    write_case(
        meta=CaseMeta(
            rel_path="f32/float32_tiny.wav",
            description="Very short file.",
            expected_action="REQUIRES_CONVERSION",
            expected_format_kind="ieee_float",
            family="tiny",
            channels=2,
            sample_rate=44100,
            bits_per_sample=32,
            format_tag="0x0003",
            subtype=None,
        ),
        fmt=fmt_float(channels=2, sample_rate=44100),
        audio_payload=pack_float32(tiny_frames),
        manifest=manifest,
    )

    write_malformed_cases(manifest)

    manifest.sort(key=lambda item: str(item["path"]))
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    generated = generate()
    print(f"Generated {len(generated)} fixture entries.")
    print(f"WAV root: {WAVS_DIR}")
    print(f"Manifest: {MANIFEST_PATH}")
