from __future__ import annotations

from pathlib import Path

from wavfix.core.models import WavFormatKind
from wavfix.core.wav_parser import parse_wav_file

from .wav_helpers import (
    FLOAT_SUBTYPE_GUID,
    PCM_SUBTYPE_GUID,
    UNSUPPORTED_SUBTYPE_GUID,
    build_extensible_wav,
    build_standard_wav,
    write_bytes,
)


def test_parse_standard_pcm(tmp_path: Path) -> None:
    wav_file = tmp_path / "pcm.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0001))
    metadata = parse_wav_file(wav_file)
    assert metadata.format_kind == WavFormatKind.PCM
    assert metadata.channels == 2
    assert metadata.sample_rate == 44100


def test_parse_standard_float(tmp_path: Path) -> None:
    wav_file = tmp_path / "float.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0003, bits_per_sample=32))

    metadata = parse_wav_file(wav_file)
    assert metadata.format_kind == WavFormatKind.IEEE_FLOAT


def test_parse_extensible_pcm(tmp_path: Path) -> None:
    wav_file = tmp_path / "ext_pcm.wav"
    write_bytes(wav_file, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))

    metadata = parse_wav_file(wav_file)
    assert metadata.format_kind == WavFormatKind.EXTENSIBLE_PCM
    assert metadata.valid_bits_per_sample == 24


def test_parse_extensible_float(tmp_path: Path) -> None:
    wav_file = tmp_path / "ext_float.wav"
    write_bytes(
        wav_file,
        build_extensible_wav(subtype_guid=FLOAT_SUBTYPE_GUID, bits_per_sample=32),
    )

    metadata = parse_wav_file(wav_file)
    assert metadata.format_kind == WavFormatKind.EXTENSIBLE_FLOAT


def test_parse_extensible_unsupported(tmp_path: Path) -> None:
    wav_file = tmp_path / "ext_unknown.wav"
    write_bytes(
        wav_file,
        build_extensible_wav(subtype_guid=UNSUPPORTED_SUBTYPE_GUID, bits_per_sample=24),
    )

    metadata = parse_wav_file(wav_file)
    assert metadata.format_kind == WavFormatKind.EXTENSIBLE_UNSUPPORTED


def test_parse_missing_fmt_is_malformed(tmp_path: Path) -> None:
    wav_file = tmp_path / "bad.wav"
    wav_file.write_bytes(b"RIFF\x10\x00\x00\x00WAVEdata\x00\x00\x00\x00")

    metadata = parse_wav_file(wav_file)
    assert metadata.format_kind == WavFormatKind.MALFORMED
    assert metadata.parse_error is not None


def test_parse_handles_chunk_padding(tmp_path: Path) -> None:
    wav_file = tmp_path / "padded.wav"
    write_bytes(
        wav_file,
        build_standard_wav(format_tag=0x0001, include_odd_junk_chunk=True),
    )

    metadata = parse_wav_file(wav_file)
    assert metadata.format_kind == WavFormatKind.PCM
    assert any(chunk.chunk_id == "JUNK" for chunk in metadata.chunks)


def test_parse_header_only_mode_skips_chunk_table(tmp_path: Path) -> None:
    wav_file = tmp_path / "header_only.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0001, frames=2048))

    metadata = parse_wav_file(wav_file, include_chunks=False)
    assert metadata.format_kind == WavFormatKind.PCM
    assert metadata.chunks == []
    assert metadata.data_offset is not None
    assert metadata.data_size is not None


def test_parse_streaming_path_does_not_use_read_bytes(tmp_path: Path, monkeypatch) -> None:
    wav_file = tmp_path / "streamed.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0001, frames=1024))

    def fail_read_bytes(_self):  # noqa: ANN001
        raise AssertionError("read_bytes should not be used by parser")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)
    metadata = parse_wav_file(wav_file)
    assert metadata.format_kind == WavFormatKind.PCM
