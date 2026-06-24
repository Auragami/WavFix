from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from wavfix.cli import main
from wavfix.core.wav_parser import parse_wav_file

from .wav_helpers import PCM_SUBTYPE_GUID, build_extensible_wav, build_standard_wav, write_bytes


def _conversion_backend_available() -> bool:
    return all(
        importlib.util.find_spec(module_name) is not None
        for module_name in ("numpy", "soundfile", "soxr")
    )


def test_cli_batch_command_processes_folder(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()

    wav_file = source / "song.wav"
    write_bytes(wav_file, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))

    exit_code = main(
        [
            str(source),
            "--batch",
            "--overwrite",
            "yes",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    out_file = output / source.name / "song.wav"
    assert out_file.exists()
    assert parse_wav_file(out_file).format_tag == 0x0001

    captured = capsys.readouterr().out
    assert "Summary: total=1" in captured
    assert "header_fixed=1" in captured


def test_cli_requires_allow_conversion_for_float(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()

    wav_file = source / "float.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0003, bits_per_sample=32))

    exit_code = main(
        [
            str(source),
            "--batch",
            "--overwrite",
            "yes",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 2
    assert not (output / source.name / "float.wav").exists()

    captured = capsys.readouterr().out
    assert "rejected=1" in captured


@pytest.mark.skipif(
    not _conversion_backend_available(),
    reason="conversion backend (numpy/soundfile/soxr) not available",
)
def test_cli_converts_float_with_allow_conversion(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()

    wav_file = source / "float.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0003, bits_per_sample=32))

    exit_code = main(
        [
            str(source),
            "--batch",
            "--allow-conversion",
            "--overwrite",
            "yes",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    out_file = output / source.name / "float.wav"
    assert out_file.exists()
    out_meta = parse_wav_file(out_file)
    assert out_meta.format_tag == 0x0001
    assert out_meta.bits_per_sample == 24

    captured = capsys.readouterr().out
    assert "converted=1" in captured
