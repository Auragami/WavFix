from __future__ import annotations

import importlib.util
import struct
import threading
from pathlib import Path

import pytest

from wavfix.core import (
    InputFileSpec,
    ProcessRequest,
    inspect_file,
    process_request,
    scan_input_specs,
    scan_inputs,
)
from wavfix.core.decisions import decide_repair_action
from wavfix.core.models import RepairAction
from wavfix.core.planning import OutputPlanContext, plan_output_path
from wavfix.core.wav_parser import parse_wav_file

from .wav_helpers import (
    PCM_SUBTYPE_GUID,
    build_extensible_wav,
    build_riff_wave,
    build_standard_wav,
    write_bytes,
)


def _conversion_backend_available() -> bool:
    return all(
        importlib.util.find_spec(module_name) is not None
        for module_name in ("numpy", "soundfile", "soxr")
    )


def test_scan_inputs_discovers_supported_files(tmp_path: Path) -> None:
    folder = tmp_path / "album"
    folder.mkdir()
    wav_file = folder / "track.wav"
    txt_file = folder / "notes.txt"
    ignored = folder / "ignore.exe"

    write_bytes(wav_file, build_standard_wav(format_tag=0x0001))
    txt_file.write_text("hello", encoding="utf-8")
    ignored.write_text("not-supported", encoding="utf-8")

    discovered = scan_inputs([folder])
    assert wav_file in discovered
    assert txt_file in discovered
    assert ignored not in discovered


def test_scan_input_specs_preserves_folder_context(tmp_path: Path) -> None:
    folder = tmp_path / "album"
    folder.mkdir()
    wav_file = folder / "track.wav"
    write_bytes(wav_file, build_standard_wav(format_tag=0x0001))

    direct = tmp_path / "single.wav"
    write_bytes(direct, build_standard_wav(format_tag=0x0001))

    specs = scan_input_specs([direct, folder])
    by_path = {spec.path: spec for spec in specs}

    assert by_path[direct].source_root is None
    assert by_path[wav_file].source_root == folder


def test_inspect_file_classification_and_action(tmp_path: Path) -> None:
    pcm = tmp_path / "pcm.wav"
    ext_pcm = tmp_path / "ext_pcm.wav"
    flt = tmp_path / "float.wav"
    note = tmp_path / "note.txt"

    write_bytes(pcm, build_standard_wav(format_tag=0x0001, bits_per_sample=24))
    write_bytes(ext_pcm, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))
    write_bytes(flt, build_standard_wav(format_tag=0x0003, bits_per_sample=32))
    note.write_text("hello", encoding="utf-8")

    inspected_pcm = inspect_file(pcm, allow_conversion=True)
    inspected_ext_pcm = inspect_file(ext_pcm, allow_conversion=True)
    inspected_float = inspect_file(flt, allow_conversion=True)
    inspected_non_wav = inspect_file(note, allow_conversion=True)

    assert inspected_pcm.color_tag == "green"
    assert inspected_ext_pcm.color_tag == "yellow"
    assert inspected_float.color_tag == "orange"
    assert inspected_non_wav.color_tag == "neutral"


def test_process_request_header_fixes_extensible_pcm(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    wav_file = source / "song.wav"
    write_bytes(wav_file, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))

    request = ProcessRequest(
        input_paths=[wav_file],
        output_dir=output,
        batch_mode=False,
        overwrite_policy="yes",
        allow_conversion=False,
    )
    result = process_request(request, max_workers=1)

    assert result.total == 1
    assert result.header_fixed == 1
    assert result.modified == 1
    assert result.errors == []

    out_file = output / "song.wav"
    out_meta = parse_wav_file(out_file)
    assert out_meta.format_tag == 0x0001


def test_process_request_rejects_conversion_without_consent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    float_wav = source / "float.wav"
    write_bytes(float_wav, build_standard_wav(format_tag=0x0003, bits_per_sample=32))

    request = ProcessRequest(
        input_paths=[float_wav],
        output_dir=output,
        batch_mode=False,
        overwrite_policy="yes",
        allow_conversion=False,
    )
    result = process_request(request, max_workers=1)

    assert result.rejected == 1
    assert result.converted == 0
    assert not (output / "float.wav").exists()


@pytest.mark.skipif(
    not _conversion_backend_available(),
    reason="conversion backend (numpy/soundfile/soxr) not available",
)
def test_process_request_converts_float(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    float_wav = source / "float.wav"
    write_bytes(float_wav, build_standard_wav(format_tag=0x0003, bits_per_sample=32))

    request = ProcessRequest(
        input_paths=[float_wav],
        output_dir=output,
        batch_mode=False,
        overwrite_policy="yes",
        allow_conversion=True,
    )
    result = process_request(request, max_workers=1)

    assert result.converted == 1
    out_meta = parse_wav_file(output / "float.wav")
    assert out_meta.format_tag == 0x0001
    assert out_meta.bits_per_sample == 24


def test_process_request_copies_non_wav_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    text_file = source / "notes.txt"
    text_file.write_text("abc", encoding="utf-8")

    request = ProcessRequest(
        input_paths=[text_file],
        output_dir=output,
        batch_mode=False,
        overwrite_policy="yes",
    )
    result = process_request(request, max_workers=1)

    assert result.unchanged == 1
    assert result.copied == 1
    assert (output / "notes.txt").read_text(encoding="utf-8") == "abc"


def test_plan_output_path_clean_suffix_single_and_batch(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()

    single_context = OutputPlanContext(
        output_dir=output,
        overwrite_policy="no",
        existing_items={"song.wav"},
    )
    single_target = plan_output_path(
        InputFileSpec(path=tmp_path / "song.wav", source_root=None),
        single_context,
    )
    assert single_target.name == "song_clean.wav"

    parent = tmp_path / "source"
    parent.mkdir()
    nested = parent / "disc1"
    nested.mkdir()
    batch_file = nested / "song.wav"

    batch_context = OutputPlanContext(
        output_dir=output,
        overwrite_policy="no",
        existing_items={"source"},
    )
    batch_target = plan_output_path(
        InputFileSpec(path=batch_file, source_root=parent),
        batch_context,
    )
    assert batch_target == output / "source_clean" / "disc1" / "song.wav"


def test_process_request_mixed_files_and_folders(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()

    source_folder = tmp_path / "album"
    source_folder.mkdir()
    nested = source_folder / "disc1"
    nested.mkdir()
    folder_wav = nested / "track.wav"
    write_bytes(folder_wav, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))

    direct_file = tmp_path / "cover.jpg"
    direct_file.write_bytes(b"img")

    specs = [
        InputFileSpec(path=folder_wav, source_root=source_folder),
        InputFileSpec(path=direct_file, source_root=None),
    ]
    request = ProcessRequest(
        output_dir=output,
        input_paths=[spec.path for spec in specs],
        overwrite_policy="yes",
        input_specs=specs,
    )
    result = process_request(request, max_workers=2)

    assert result.total == 2
    assert (output / "album" / "disc1" / "track.wav").exists()
    assert (output / "cover.jpg").exists()


def test_in_place_processing_uses_temp_file(tmp_path: Path) -> None:
    wav_file = tmp_path / "song.wav"
    write_bytes(wav_file, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))

    request = ProcessRequest(
        input_paths=[wav_file],
        output_dir=tmp_path,
        batch_mode=False,
        overwrite_policy="yes",
    )
    result = process_request(request, max_workers=1)

    assert result.total == 1
    assert result.header_fixed == 1
    assert parse_wav_file(wav_file).format_tag == 0x0001


def test_process_result_counts_and_progress_events(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    ext_pcm = source / "ext_pcm.wav"
    float_wav = source / "float.wav"
    note = source / "note.txt"
    write_bytes(ext_pcm, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))
    write_bytes(float_wav, build_standard_wav(format_tag=0x0003, bits_per_sample=32))
    note.write_text("ok", encoding="utf-8")

    events: list[str] = []

    def callback(event) -> None:
        events.append(event.kind)

    request = ProcessRequest(
        input_paths=[ext_pcm, float_wav, note],
        output_dir=output,
        batch_mode=False,
        overwrite_policy="yes",
        allow_conversion=False,
    )
    result = process_request(request, progress_callback=callback, max_workers=1)

    assert result.total == 3
    assert result.header_fixed == 1
    assert result.unchanged == 1
    assert result.rejected == 1
    assert result.converted == 0
    assert events[-1] == "done"


def test_process_request_callback_can_capture_non_pickleable_state(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    wav_file = source / "song.wav"
    write_bytes(wav_file, build_extensible_wav(subtype_guid=PCM_SUBTYPE_GUID, bits_per_sample=24))

    lock = threading.Lock()
    seen: list[str] = []

    def callback(event) -> None:
        with lock:
            seen.append(event.kind)

    request = ProcessRequest(
        input_paths=[wav_file],
        output_dir=output,
        batch_mode=False,
        overwrite_policy="yes",
    )
    result = process_request(request, progress_callback=callback, max_workers=1)

    assert result.header_fixed == 1
    assert "file" in seen


def test_decision_sample_rate_policy_convert_nearest(tmp_path: Path) -> None:
    wav_file = tmp_path / "rate_50000.wav"
    write_bytes(
        wav_file,
        build_standard_wav(format_tag=0x0001, sample_rate=50000, bits_per_sample=16),
    )
    metadata = parse_wav_file(wav_file, include_chunks=False)
    decision = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=True,
        multichannel_policy="reject",
        sample_rate_policy="convert_nearest",
        bit_depth_policy="convert",
    )

    assert decision.action == RepairAction.CONVERT
    assert decision.target is not None
    assert decision.target.sample_rate == 48000
    assert decision.target.bit_depth == 16


def test_decision_sample_rate_tie_chooses_lower_supported_rate(tmp_path: Path) -> None:
    wav_file = tmp_path / "rate_68100.wav"
    write_bytes(
        wav_file,
        build_standard_wav(format_tag=0x0001, sample_rate=68100, bits_per_sample=24),
    )
    metadata = parse_wav_file(wav_file, include_chunks=False)
    decision = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=True,
        multichannel_policy="reject",
        sample_rate_policy="convert_nearest",
        bit_depth_policy="convert",
    )
    assert decision.action == RepairAction.CONVERT
    assert decision.target is not None
    assert decision.target.sample_rate == 48000


def test_decision_sample_rate_policy_reject_unsupported(tmp_path: Path) -> None:
    wav_file = tmp_path / "rate_50000.wav"
    write_bytes(
        wav_file,
        build_standard_wav(format_tag=0x0001, sample_rate=50000, bits_per_sample=16),
    )
    metadata = parse_wav_file(wav_file, include_chunks=False)
    decision = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=True,
        multichannel_policy="reject",
        sample_rate_policy="reject_unsupported",
        bit_depth_policy="convert",
    )

    assert decision.action == RepairAction.REJECT
    assert "sample rate" in decision.reason.lower()


def test_decision_bit_depth_policy_convert_or_reject(tmp_path: Path) -> None:
    wav_file = tmp_path / "bits_20.wav"
    write_bytes(
        wav_file,
        build_standard_wav(format_tag=0x0001, sample_rate=44100, bits_per_sample=20),
    )
    metadata = parse_wav_file(wav_file, include_chunks=False)

    convert_decision = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=True,
        multichannel_policy="reject",
        sample_rate_policy="convert_nearest",
        bit_depth_policy="convert",
    )
    assert convert_decision.action == RepairAction.CONVERT
    assert convert_decision.target is not None
    assert convert_decision.target.bit_depth == 24

    reject_decision = decide_repair_action(
        metadata,
        profile_name="preserve_supported_rate",
        allow_conversion=True,
        multichannel_policy="reject",
        sample_rate_policy="convert_nearest",
        bit_depth_policy="reject_unsupported",
    )
    assert reject_decision.action == RepairAction.REJECT
    assert "bit depth" in reject_decision.reason.lower()


def test_short_status_uses_convert_label(tmp_path: Path) -> None:
    float_wav = tmp_path / "float.wav"
    write_bytes(float_wav, build_standard_wav(format_tag=0x0003, bits_per_sample=32))
    inspection = inspect_file(float_wav, allow_conversion=True)
    assert inspection.action == RepairAction.CONVERT
    from wavfix.core.inspection import short_status

    assert short_status(inspection) == "Convert"


def test_inspection_strict_preserve_still_marks_conversion_when_metadata_supported(
    tmp_path: Path,
) -> None:
    float_wav = tmp_path / "float_strict.wav"
    write_bytes(float_wav, build_standard_wav(format_tag=0x0003, bits_per_sample=32))
    inspection = inspect_file(
        float_wav,
        allow_conversion=True,
        metadata_policy="strict_preserve",
    )
    assert inspection.action == RepairAction.CONVERT


def test_strict_metadata_policy_rejects_unsupported_chunk_during_conversion(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    float_wav = source / "float_with_unknown_meta.wav"
    channels = 2
    sample_rate = 44100
    bits_per_sample = 32
    block_align = channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    fmt_payload = struct.pack(
        "<HHIIHH",
        0x0003,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )
    float_data = struct.pack("<f", 0.25) * 16
    payload = build_riff_wave(
        [
            (b"fmt ", fmt_payload),
            (b"zzzz", b"meta"),
            (b"data", float_data),
        ]
    )
    write_bytes(float_wav, payload)

    inspection = inspect_file(
        float_wav,
        allow_conversion=True,
        metadata_policy="strict_preserve",
    )
    assert inspection.action == RepairAction.REJECT
    assert "unsupported metadata chunk" in inspection.reason.lower()

    request = ProcessRequest(
        input_paths=[float_wav],
        output_dir=output,
        overwrite_policy="yes",
        allow_conversion=True,
        metadata_policy="strict_preserve",
    )
    result = process_request(request, max_workers=1)
    assert result.rejected == 1
    assert result.converted == 0
    assert not (output / "float_with_unknown_meta.wav").exists()
