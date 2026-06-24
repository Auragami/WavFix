from __future__ import annotations

import struct
from pathlib import Path

PCM_SUBTYPE_GUID = bytes.fromhex("0100000000001000800000aa00389b71")
FLOAT_SUBTYPE_GUID = bytes.fromhex("0300000000001000800000aa00389b71")
UNSUPPORTED_SUBTYPE_GUID = bytes.fromhex("9900000000001000800000aa00389b71")


def build_riff_wave(chunks: list[tuple[bytes, bytes]]) -> bytes:
    body = bytearray()
    for chunk_id, payload in chunks:
        body.extend(chunk_id)
        body.extend(struct.pack("<I", len(payload)))
        body.extend(payload)
        if len(payload) % 2:
            body.append(0)

    riff_size = 4 + len(body)
    return b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + bytes(body)


def _pcm_data(channels: int, bits_per_sample: int, frames: int) -> bytes:
    bytes_per_sample = bits_per_sample // 8
    block_align = channels * bytes_per_sample
    return bytes([0x11] * (frames * block_align))


def _float_data(channels: int, frames: int) -> bytes:
    payload = bytearray()
    for _ in range(frames * channels):
        payload.extend(struct.pack("<f", 0.25))
    return bytes(payload)


def build_standard_wav(
    *,
    format_tag: int,
    channels: int = 2,
    sample_rate: int = 44100,
    bits_per_sample: int = 16,
    frames: int = 8,
    include_odd_junk_chunk: bool = False,
) -> bytes:
    block_align = channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    fmt_payload = struct.pack(
        "<HHIIHH",
        format_tag,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )

    if format_tag == 0x0003:
        data_payload = _float_data(channels, frames)
    else:
        data_payload = _pcm_data(channels, bits_per_sample, frames)

    chunks: list[tuple[bytes, bytes]] = [(b"fmt ", fmt_payload)]
    if include_odd_junk_chunk:
        chunks.append((b"JUNK", b"abc"))
    chunks.append((b"data", data_payload))
    return build_riff_wave(chunks)


def build_extensible_wav(
    *,
    subtype_guid: bytes,
    channels: int = 2,
    sample_rate: int = 44100,
    bits_per_sample: int = 24,
    valid_bits_per_sample: int | None = None,
    channel_mask: int = 0,
    frames: int = 8,
) -> bytes:
    if valid_bits_per_sample is None:
        valid_bits_per_sample = bits_per_sample

    block_align = channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    cb_size = 22
    fmt_payload = struct.pack(
        "<HHIIHHH",
        0xFFFE,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        cb_size,
    )
    fmt_payload += struct.pack("<HI", valid_bits_per_sample, channel_mask)
    fmt_payload += subtype_guid

    if subtype_guid == FLOAT_SUBTYPE_GUID:
        data_payload = _float_data(channels, frames)
    else:
        data_payload = _pcm_data(channels, bits_per_sample, frames)

    return build_riff_wave([(b"fmt ", fmt_payload), (b"data", data_payload)])


def write_bytes(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)
