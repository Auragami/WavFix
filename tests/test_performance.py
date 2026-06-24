from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np

import wavfix.core.processing as processing_module
from wavfix.core import ProcessRequest, process_request
from wavfix.core.processing import resolve_performance_config

from .wav_helpers import build_standard_wav, write_bytes


def test_resolve_performance_config_profiles() -> None:
    conservative = resolve_performance_config("conservative", cpu_count=8)
    balanced = resolve_performance_config("balanced", cpu_count=8)
    fast = resolve_performance_config("fast", cpu_count=8)

    assert conservative.worker_count == 4
    assert conservative.conversion_slots == 1
    assert conservative.resample_quality == "HQ"

    assert balanced.worker_count == 6
    assert balanced.conversion_slots == 2
    assert balanced.resample_quality == "VHQ"

    assert fast.worker_count == 7
    assert fast.conversion_slots == 2
    assert fast.resample_quality == "HQ"


def test_resolve_performance_config_stays_bounded_on_low_core_machines() -> None:
    dual_core_balanced = resolve_performance_config("balanced", cpu_count=2)
    dual_core_fast = resolve_performance_config("fast", cpu_count=2)
    quad_core_fast = resolve_performance_config("fast", cpu_count=4)

    assert dual_core_balanced.worker_count == 1
    assert dual_core_balanced.conversion_slots == 1

    assert dual_core_fast.worker_count == 1
    assert dual_core_fast.conversion_slots == 1

    assert quad_core_fast.worker_count == 3
    assert quad_core_fast.conversion_slots == 1


def test_conversion_throttling_respects_conservative_slots(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    wav_files = []
    for index in range(5):
        wav_file = source / f"track_{index}.wav"
        write_bytes(wav_file, build_standard_wav(format_tag=0x0003, bits_per_sample=32))
        wav_files.append(wav_file)

    lock = threading.Lock()
    active = 0
    max_active = 0

    def fake_run_conversion(  # noqa: ANN001
        *,
        input_file,
        output_file,
        target,
        input_metadata,
        metadata_policy,
        resample_quality,
    ):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.03)
        output_file.write_bytes(input_file.read_bytes())
        with lock:
            active -= 1
        return []

    monkeypatch.setattr(processing_module, "_run_conversion", fake_run_conversion)
    monkeypatch.setattr(processing_module, "_validate_conversion_output", lambda **_kwargs: None)

    request = ProcessRequest(
        input_paths=wav_files,
        output_dir=output,
        overwrite_policy="yes",
        allow_conversion=True,
        performance_mode="conservative",
    )

    result = process_request(request, max_workers=6)

    assert result.converted == 5
    assert result.errors == []
    assert max_active <= 1


def test_perceptual_downmix_uses_channel_mask() -> None:
    # FL, FR, FC channel mask for 3-channel input.
    channel_mask = (1 << 0) | (1 << 1) | (1 << 2)
    samples = np.array([[0.0, 0.0, 1.0]], dtype=np.float64)

    out = processing_module._to_aligned_channels(
        np,
        samples,
        target_channels=2,
        channel_mask=channel_mask,
    )
    assert out.shape == (1, 2)
    # Center channel should map equally to L/R.
    assert np.isclose(float(out[0, 0]), float(out[0, 1]))


def test_quantize_reports_clipped_samples() -> None:
    samples = np.array(
        [[1.2, -1.3], [0.2, -0.2], [2.0, -2.0]],
        dtype=np.float64,
    )
    quantized, clipped = processing_module._quantize_pcm_float(np, samples, 24)
    assert quantized.shape == samples.shape
    assert clipped == 4


def test_downmix_without_mask_is_deterministic() -> None:
    samples = np.array(
        [[0.1, 0.2, 0.3, 0.4], [-0.2, 0.1, 0.0, -0.1]],
        dtype=np.float64,
    )
    out_a = processing_module._to_aligned_channels(
        np,
        samples,
        target_channels=2,
        channel_mask=None,
    )
    out_b = processing_module._to_aligned_channels(
        np,
        samples,
        target_channels=2,
        channel_mask=None,
    )
    assert np.allclose(out_a, out_b)


def test_run_conversion_streams_with_blocks(monkeypatch, tmp_path: Path) -> None:
    class FakeInputFile:
        samplerate = 48000

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def blocks(self, *, blocksize, dtype, always_2d):  # noqa: ANN001
            assert blocksize > 0
            assert dtype == "float64"
            assert always_2d is True
            yield np.zeros((128, 2), dtype=np.float64)
            yield np.ones((64, 2), dtype=np.float64) * 0.1

    class FakeOutputFile:
        def __init__(self):
            self.writes: list[np.ndarray] = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def write(self, data):  # noqa: ANN001
            self.writes.append(np.array(data, copy=True))

    fake_output = FakeOutputFile()

    class FakeSoundfileModule:
        def SoundFile(self, _path, mode="r", **_kwargs):  # noqa: ANN001
            if mode == "r":
                return FakeInputFile()
            return fake_output

    class FakeSoxrModule:
        @staticmethod
        def resample(block, _in_rate, _out_rate, quality="HQ"):  # noqa: ANN001
            assert quality in {"HQ", "VHQ"}
            return block

    monkeypatch.setattr(
        processing_module,
        "_load_conversion_backends",
        lambda: (np, FakeSoundfileModule(), FakeSoxrModule()),
    )

    metadata = processing_module.WavMetadata(
        path=tmp_path / "in.wav",
        riff_valid=True,
        wave_valid=True,
        format_kind=processing_module.WavFormatKind.IEEE_FLOAT,
        channels=2,
        sample_rate=48000,
        bits_per_sample=32,
    )
    warnings = processing_module._run_conversion(
        input_file=tmp_path / "in.wav",
        output_file=tmp_path / "out.wav",
        target=processing_module.ConversionTarget(sample_rate=48000, channels=2, bit_depth=24),
        input_metadata=metadata,
        metadata_policy="best_effort",
        resample_quality="HQ",
    )

    assert warnings == []
    assert len(fake_output.writes) == 2
