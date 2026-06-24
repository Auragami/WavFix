#!/usr/bin/env python3
"""Lightweight performance benchmark helper for WavFix hotspot checks."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wavfix.core.inspection import inspect_file
from wavfix.core.models import ProcessRequest
from wavfix.core.processing import process_request
from wavfix.core.scanner import scan_input_specs

PASS_FIXTURE = REPO_ROOT / "tests/wav_test_suite/wavs/pcm/pcm_stereo_44100_24.wav"
CONVERT_FIXTURE = REPO_ROOT / "tests/wav_test_suite/wavs/f32/float32_stereo_44100.wav"


def _clone_fixture(source: Path, target_dir: Path, count: int) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for index in range(count):
        destination = target_dir / f"sample_{index:05d}{source.suffix}"
        shutil.copyfile(source, destination)
        copied.append(destination)
    return copied


def _bench_pass_through(*, file_count: int, workers: int) -> tuple[float, float]:
    with tempfile.TemporaryDirectory(prefix="wavfix_bench_pass_") as input_tmp:
        with tempfile.TemporaryDirectory(prefix="wavfix_bench_pass_out_") as output_tmp:
            input_paths = _clone_fixture(PASS_FIXTURE, Path(input_tmp), file_count)
            request = ProcessRequest(
                output_dir=Path(output_tmp),
                input_paths=input_paths,
                overwrite_policy="yes",
                allow_conversion=False,
                profile="preserve_supported_rate",
                multichannel_policy="reject",
                metadata_policy="best_effort",
                sample_rate_policy="convert_nearest",
                bit_depth_policy="convert",
                performance_mode="balanced",
            )
            start = time.perf_counter()
            process_request(request, max_workers=workers)
            elapsed = time.perf_counter() - start
            return elapsed, file_count / elapsed if elapsed > 0 else 0.0


def _bench_conversion(*, file_count: int, workers: int) -> tuple[float, float]:
    with tempfile.TemporaryDirectory(prefix="wavfix_bench_conv_") as input_tmp:
        with tempfile.TemporaryDirectory(prefix="wavfix_bench_conv_out_") as output_tmp:
            input_paths = _clone_fixture(CONVERT_FIXTURE, Path(input_tmp), file_count)
            request = ProcessRequest(
                output_dir=Path(output_tmp),
                input_paths=input_paths,
                overwrite_policy="yes",
                allow_conversion=True,
                profile="preserve_supported_rate",
                multichannel_policy="downmix",
                metadata_policy="best_effort",
                sample_rate_policy="convert_nearest",
                bit_depth_policy="convert",
                performance_mode="balanced",
            )
            start = time.perf_counter()
            process_request(request, max_workers=workers)
            elapsed = time.perf_counter() - start
            return elapsed, file_count / elapsed if elapsed > 0 else 0.0


def _bench_load_and_reinspect(*, file_count: int) -> tuple[float, float, float]:
    with tempfile.TemporaryDirectory(prefix="wavfix_bench_load_") as root_tmp:
        root_path = Path(root_tmp) / "inputs"
        _clone_fixture(PASS_FIXTURE, root_path, file_count)
        selected_specs = scan_input_specs([root_path])

        scan_start = time.perf_counter()
        _ = scan_input_specs([root_path])
        scan_elapsed = time.perf_counter() - scan_start

        serial_start = time.perf_counter()
        _ = [
            inspect_file(
                spec.path,
                profile_name="preserve_supported_rate",
                allow_conversion=True,
                multichannel_policy="reject",
                metadata_policy="best_effort",
                sample_rate_policy="convert_nearest",
                bit_depth_policy="convert",
            )
            for spec in selected_specs
        ]
        serial_elapsed = time.perf_counter() - serial_start

        parallel_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as executor:
            _ = list(
                executor.map(
                    lambda spec: inspect_file(
                        spec.path,
                        profile_name="preserve_supported_rate",
                        allow_conversion=True,
                        multichannel_policy="reject",
                        metadata_policy="best_effort",
                        sample_rate_policy="convert_nearest",
                        bit_depth_policy="convert",
                    ),
                    selected_specs,
                )
            )
        parallel_elapsed = time.perf_counter() - parallel_start
        return scan_elapsed, serial_elapsed, parallel_elapsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local WavFix performance benchmarks.")
    parser.add_argument(
        "--pass-files",
        type=int,
        default=800,
        help="Number of pass-through fixture files to benchmark.",
    )
    parser.add_argument(
        "--convert-files",
        type=int,
        default=120,
        help="Number of conversion fixture files to benchmark.",
    )
    parser.add_argument(
        "--inspect-files",
        type=int,
        default=1000,
        help="Number of files for scan/reinspect benchmark.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Worker count override for processing benchmarks.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    pass_elapsed, pass_tput = _bench_pass_through(file_count=args.pass_files, workers=args.workers)
    convert_elapsed, convert_tput = _bench_conversion(
        file_count=args.convert_files,
        workers=args.workers,
    )
    scan_elapsed, serial_elapsed, parallel_elapsed = _bench_load_and_reinspect(
        file_count=args.inspect_files
    )

    print("WavFix benchmark summary")
    print(f"pass_through: {pass_elapsed:.3f}s ({pass_tput:.1f} files/s)")
    print(f"conversion:   {convert_elapsed:.3f}s ({convert_tput:.1f} files/s)")
    print(f"scan:         {scan_elapsed:.3f}s")
    print(f"reinspect_serial:   {serial_elapsed:.3f}s")
    print(f"reinspect_parallel: {parallel_elapsed:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
