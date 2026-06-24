from __future__ import annotations

from pathlib import Path

from wavfix.core.decisions import decide_repair_action
from wavfix.core.models import RepairAction
from wavfix.core.wav_parser import parse_wav_file

from .wav_helpers import (
    FLOAT_SUBTYPE_GUID,
    PCM_SUBTYPE_GUID,
    build_extensible_wav,
    build_standard_wav,
    write_bytes,
)


def test_decision_pass_through_for_compatible_pcm(tmp_path: Path) -> None:
    wav_file = tmp_path / "pcm.wav"
    write_bytes(
        wav_file,
        build_standard_wav(format_tag=0x0001, sample_rate=44100, bits_per_sample=24),
    )

    metadata = parse_wav_file(wav_file)
    outcome = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=False,
        multichannel_policy="reject",
    )
    assert outcome.action == RepairAction.PASS_THROUGH


def test_decision_header_fix_for_extensible_pcm(tmp_path: Path) -> None:
    wav_file = tmp_path / "ext_pcm.wav"
    write_bytes(wav_file, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))

    metadata = parse_wav_file(wav_file)
    outcome = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=False,
        multichannel_policy="reject",
    )
    assert outcome.action == RepairAction.HEADER_FIX


def test_decision_rejects_float_without_conversion_consent(tmp_path: Path) -> None:
    wav_file = tmp_path / "float.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0003, bits_per_sample=32))

    metadata = parse_wav_file(wav_file)
    outcome = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=False,
        multichannel_policy="reject",
    )
    assert outcome.action == RepairAction.REJECT


def test_decision_converts_float_when_allowed(tmp_path: Path) -> None:
    wav_file = tmp_path / "float.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0003, bits_per_sample=32))

    metadata = parse_wav_file(wav_file)
    outcome = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=True,
        multichannel_policy="reject",
    )
    assert outcome.action == RepairAction.CONVERT
    assert outcome.target is not None
    assert outcome.target.bit_depth == 24


def test_decision_extensible_float_never_header_fix(tmp_path: Path) -> None:
    wav_file = tmp_path / "ext_float.wav"
    write_bytes(
        wav_file,
        build_extensible_wav(subtype_guid=FLOAT_SUBTYPE_GUID, bits_per_sample=32),
    )

    metadata = parse_wav_file(wav_file)
    outcome = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=True,
        multichannel_policy="reject",
    )
    assert outcome.action == RepairAction.CONVERT
