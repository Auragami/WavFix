"""RIFF/WAVE parsing and format classification."""

from __future__ import annotations

import struct
from io import BufferedReader
from pathlib import Path

from .models import WavChunk, WavFormatKind, WavMetadata

WAVE_FORMAT_PCM = 0x0001
WAVE_FORMAT_IEEE_FLOAT = 0x0003
WAVE_FORMAT_EXTENSIBLE = 0xFFFE

PCM_SUBTYPE_GUID = bytes.fromhex("0100000000001000800000aa00389b71")
FLOAT_SUBTYPE_GUID = bytes.fromhex("0300000000001000800000aa00389b71")


def _classify_from_fmt(metadata: WavMetadata, fmt_payload: bytes) -> WavMetadata:
    if len(fmt_payload) < 16:
        metadata.parse_error = "fmt chunk is too short."
        metadata.format_kind = WavFormatKind.MALFORMED
        return metadata

    (
        metadata.format_tag,
        metadata.channels,
        metadata.sample_rate,
        metadata.byte_rate,
        metadata.block_align,
        metadata.bits_per_sample,
    ) = struct.unpack_from("<HHIIHH", fmt_payload, 0)

    if metadata.format_tag == WAVE_FORMAT_PCM:
        metadata.format_kind = WavFormatKind.PCM
        return metadata

    if metadata.format_tag == WAVE_FORMAT_IEEE_FLOAT:
        metadata.format_kind = WavFormatKind.IEEE_FLOAT
        return metadata

    if metadata.format_tag != WAVE_FORMAT_EXTENSIBLE:
        metadata.format_kind = WavFormatKind.UNSUPPORTED
        return metadata

    if len(fmt_payload) < 40:
        metadata.parse_error = "Extensible fmt chunk is too short."
        metadata.format_kind = WavFormatKind.MALFORMED
        return metadata

    cb_size = struct.unpack_from("<H", fmt_payload, 16)[0]
    if cb_size < 22:
        metadata.parse_error = "Extensible fmt cbSize is smaller than required."
        metadata.format_kind = WavFormatKind.MALFORMED
        return metadata

    metadata.valid_bits_per_sample = struct.unpack_from("<H", fmt_payload, 18)[0]
    metadata.channel_mask = struct.unpack_from("<I", fmt_payload, 20)[0]
    metadata.subtype_guid = fmt_payload[24:40]

    if metadata.subtype_guid == PCM_SUBTYPE_GUID:
        metadata.format_kind = WavFormatKind.EXTENSIBLE_PCM
    elif metadata.subtype_guid == FLOAT_SUBTYPE_GUID:
        metadata.format_kind = WavFormatKind.EXTENSIBLE_FLOAT
    else:
        metadata.format_kind = WavFormatKind.EXTENSIBLE_UNSUPPORTED

    return metadata


def _read_exact(handle: BufferedReader, size: int) -> bytes | None:
    data = handle.read(size)
    if len(data) != size:
        return None
    return data


def parse_wav_file(path: Path | str, *, include_chunks: bool = True) -> WavMetadata:
    """Parse a WAV file and return structured metadata for safe processing decisions."""
    file_path = Path(path)
    metadata = WavMetadata(path=file_path, riff_valid=False, wave_valid=False)

    try:
        file_size = file_path.stat().st_size
        with file_path.open("rb") as handle:
            header = _read_exact(handle, 12)
            if header is None:
                metadata.parse_error = "File is too short to be a valid RIFF/WAVE file."
                metadata.format_kind = WavFormatKind.MALFORMED
                return metadata

            if header[:4] != b"RIFF":
                metadata.parse_error = "RIFF header missing."
                metadata.format_kind = WavFormatKind.MALFORMED
                return metadata
            metadata.riff_valid = True
            metadata.riff_size = struct.unpack_from("<I", header, 4)[0]

            if header[8:12] != b"WAVE":
                metadata.parse_error = "WAVE signature missing."
                metadata.format_kind = WavFormatKind.MALFORMED
                return metadata
            metadata.wave_valid = True

            offset = 12
            handle.seek(offset)
            fmt_payload: bytes | None = None
            while offset + 8 <= file_size:
                chunk_header = _read_exact(handle, 8)
                if chunk_header is None:
                    metadata.parse_error = "Chunk header could not be read."
                    metadata.format_kind = WavFormatKind.MALFORMED
                    return metadata

                chunk_id = chunk_header[:4]
                chunk_size = struct.unpack_from("<I", chunk_header, 4)[0]
                data_offset = offset + 8
                data_end = data_offset + chunk_size
                if data_end > file_size:
                    metadata.parse_error = "Chunk size exceeds file bounds."
                    metadata.format_kind = WavFormatKind.MALFORMED
                    return metadata

                padded_size = chunk_size + (chunk_size % 2)
                if include_chunks:
                    metadata.chunks.append(
                        WavChunk(
                            chunk_id=chunk_id.decode("ascii", errors="replace"),
                            offset=offset,
                            size=chunk_size,
                            data_offset=data_offset,
                            padded_size=padded_size,
                        )
                    )

                if chunk_id == b"fmt " and fmt_payload is None:
                    metadata.fmt_offset = offset
                    metadata.fmt_size = chunk_size
                    fmt_payload = _read_exact(handle, chunk_size)
                    if fmt_payload is None:
                        metadata.parse_error = "fmt chunk payload could not be read."
                        metadata.format_kind = WavFormatKind.MALFORMED
                        return metadata
                elif chunk_id == b"data" and metadata.data_offset is None:
                    metadata.data_offset = data_offset
                    metadata.data_size = chunk_size
                    if chunk_size:
                        handle.seek(chunk_size, 1)
                else:
                    if chunk_size:
                        handle.seek(chunk_size, 1)

                if chunk_size % 2:
                    padding = _read_exact(handle, 1)
                    if padding is None:
                        metadata.parse_error = "Chunk padding exceeds file bounds."
                        metadata.format_kind = WavFormatKind.MALFORMED
                        return metadata

                offset = data_offset + padded_size

            if fmt_payload is None:
                metadata.parse_error = "Missing fmt chunk."
                metadata.format_kind = WavFormatKind.MALFORMED
                return metadata
            if metadata.data_offset is None:
                metadata.parse_error = "Missing data chunk."
                metadata.format_kind = WavFormatKind.MALFORMED
                return metadata

            return _classify_from_fmt(metadata, fmt_payload)
    except OSError as exc:
        metadata.parse_error = str(exc)
        metadata.format_kind = WavFormatKind.MALFORMED
        return metadata


def parse_wav_header(path: Path | str) -> WavMetadata:
    """Parse WAV metadata without retaining a full chunk table."""
    return parse_wav_file(path, include_chunks=False)
