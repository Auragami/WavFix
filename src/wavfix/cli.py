"""Command-line interface for WavFix."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from .core import InputFileSpec, ProcessRequest, process_request, scan_input_specs
from .core.models import (
    BitDepthPolicy,
    ConverterBackend,
    MetadataPolicy,
    MultiChannelPolicy,
    PerformanceMode,
    ProfileName,
    SampleRatePolicy,
)
from .core.planning import safe_common_parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WavFix CLI")
    parser.add_argument("inputs", nargs="+", help="Input files or directories")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Preserve folder structure under a top-level source folder name",
    )
    parser.add_argument(
        "--overwrite",
        choices=["yes", "no", "ask"],
        default="ask",
        help="Overwrite policy for existing output paths",
    )
    parser.add_argument(
        "--profile",
        choices=["preserve_supported_rate", "universal_pioneer_safe"],
        default="preserve_supported_rate",
        help="Compatibility profile used to decide pass-through/fix/convert behavior",
    )
    parser.add_argument(
        "--multichannel-policy",
        choices=["reject", "downmix"],
        default="downmix",
        help="How to handle multichannel input",
    )
    parser.add_argument(
        "--metadata-policy",
        choices=["best_effort", "strict_preserve"],
        default="best_effort",
        help="Metadata preservation policy used during conversion",
    )
    parser.add_argument(
        "--allow-conversion",
        action="store_true",
        help="Allow actions that modify audio data (required for conversion)",
    )
    parser.add_argument(
        "--sample-rate-policy",
        choices=["convert_nearest", "reject_unsupported"],
        default="convert_nearest",
        help="How unsupported sample rates are handled",
    )
    parser.add_argument(
        "--bit-depth-policy",
        choices=["convert", "reject_unsupported"],
        default="convert",
        help="How unsupported bit depths are handled",
    )
    parser.add_argument(
        "--performance-mode",
        choices=["conservative", "balanced", "fast"],
        default="balanced",
        help="Processing speed profile balancing throughput and system impact",
    )
    parser.add_argument(
        "--converter-backend",
        choices=["builtin", "ffmpeg"],
        default="builtin",
        help="Audio conversion backend to use when conversion is allowed",
    )
    parser.add_argument(
        "--ffmpeg-path",
        default="",
        help="Path to ffmpeg executable when --converter-backend=ffmpeg; empty uses PATH",
    )
    return parser


def _prompt_overwrite() -> bool:
    answer = input("Overwrite existing files/folder? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_specs = scan_input_specs(args.inputs)
    if not input_specs:
        print("No supported files were found in the provided inputs.")
        return 1

    if args.batch:
        common_root = safe_common_parent([spec.path for spec in input_specs])
        input_specs = [
            InputFileSpec(path=spec.path, source_root=common_root) for spec in input_specs
        ]

    request = ProcessRequest(
        output_dir=Path(args.output),
        input_paths=[spec.path for spec in input_specs],
        batch_mode=args.batch,
        overwrite_policy=args.overwrite,
        input_specs=input_specs,
        profile=cast(ProfileName, args.profile),
        performance_mode=cast(PerformanceMode, args.performance_mode),
        allow_conversion=args.allow_conversion,
        multichannel_policy=cast(MultiChannelPolicy, args.multichannel_policy),
        metadata_policy=cast(MetadataPolicy, args.metadata_policy),
        sample_rate_policy=cast(SampleRatePolicy, args.sample_rate_policy),
        bit_depth_policy=cast(BitDepthPolicy, args.bit_depth_policy),
        converter_backend=cast(ConverterBackend, args.converter_backend),
        ffmpeg_path=args.ffmpeg_path,
    )

    def progress(event) -> None:
        print(event.message)

    result = process_request(
        request,
        progress_callback=progress,
        overwrite_resolver=_prompt_overwrite if args.overwrite == "ask" else None,
    )

    print(
        "Summary: "
        f"total={result.total}, "
        f"unchanged={result.unchanged}, "
        f"header_fixed={result.header_fixed}, "
        f"converted={result.converted}, "
        f"rejected={result.rejected}, "
        f"errors={len(result.errors)}"
    )

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")

    if result.errors or result.rejected > 0:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
