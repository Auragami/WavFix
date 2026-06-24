"""Run parser/decision/planner/processing checks against WAV fixture manifest.

Usage:
  python tests/wav_test_suite/wav_test_suite.py
  python tests/wav_test_suite/wav_test_suite.py --regen
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from generate_wavs import BASE_DIR, MANIFEST_PATH, WAVS_DIR, generate

from wavfix.core.decisions import decide_repair_action
from wavfix.core.models import InputFileSpec, ProcessRequest, RepairAction, WavFormatKind
from wavfix.core.planning import OutputPlanContext, plan_output_path
from wavfix.core.processing import process_request
from wavfix.core.scanner import scan_input_specs
from wavfix.core.wav_parser import parse_wav_file


@dataclass(frozen=True, slots=True)
class ManifestCase:
    filename: str
    path: str
    description: str
    expected_action: str
    expected_format_kind: str
    family: str
    channels: int | None
    sample_rate: int | None
    bits_per_sample: int | None
    format_tag: str | None
    subtype: str | None


def _load_manifest() -> list[ManifestCase]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    cases: list[ManifestCase] = []
    for item in payload:
        cases.append(
            ManifestCase(
                filename=str(item["filename"]),
                path=str(item["path"]),
                description=str(item["description"]),
                expected_action=str(item["expected_action"]),
                expected_format_kind=str(item["expected_format_kind"]),
                family=str(item["family"]),
                channels=item.get("channels"),
                sample_rate=item.get("sample_rate"),
                bits_per_sample=item.get("bits_per_sample"),
                format_tag=item.get("format_tag"),
                subtype=item.get("subtype"),
            )
        )
    return cases


def _kind_from_expected(name: str) -> WavFormatKind:
    mapping = {
        "pcm": WavFormatKind.PCM,
        "ieee_float": WavFormatKind.IEEE_FLOAT,
        "extensible_pcm": WavFormatKind.EXTENSIBLE_PCM,
        "extensible_float": WavFormatKind.EXTENSIBLE_FLOAT,
        "extensible_unsupported": WavFormatKind.EXTENSIBLE_UNSUPPORTED,
        "malformed": WavFormatKind.MALFORMED,
    }
    if name not in mapping:
        raise AssertionError(f"Unknown expected_format_kind value: {name}")
    return mapping[name]


def _assert_parser(cases: list[ManifestCase]) -> None:
    for case in cases:
        path = BASE_DIR / case.path
        metadata = parse_wav_file(path)
        expected_kind = _kind_from_expected(case.expected_format_kind)
        assert metadata.format_kind == expected_kind, (
            f"[parser] {case.filename}: expected {expected_kind}, got {metadata.format_kind}"
        )

        if case.channels is not None:
            assert metadata.channels == case.channels, (
                f"[parser] channels mismatch for {case.filename}"
            )
        if case.sample_rate is not None:
            assert metadata.sample_rate == case.sample_rate, (
                f"[parser] sample_rate mismatch for {case.filename}"
            )
        if case.bits_per_sample is not None:
            assert metadata.bits_per_sample == case.bits_per_sample, (
                f"[parser] bits_per_sample mismatch for {case.filename}"
            )


def _assert_decisions(cases: list[ManifestCase]) -> None:
    for case in cases:
        path = BASE_DIR / case.path
        metadata = parse_wav_file(path)
        decision = decide_repair_action(
            metadata,
            profile_name="preserve_supported_rate",
            allow_conversion=True,
            multichannel_policy="reject",
            sample_rate_policy="convert_nearest",
            bit_depth_policy="convert",
        )

        if case.expected_action == "SHOULD_PASS":
            assert decision.action == RepairAction.PASS_THROUGH, f"[decision] {case.filename}"
        elif case.expected_action == "SAFE_HEADER_FIX":
            assert decision.action == RepairAction.HEADER_FIX, f"[decision] {case.filename}"
        elif case.expected_action == "REQUIRES_CONVERSION":
            assert decision.action == RepairAction.CONVERT, f"[decision] {case.filename}"
            reject_no_consent = decide_repair_action(
                metadata,
                profile_name="preserve_supported_rate",
                allow_conversion=False,
                multichannel_policy="reject",
                sample_rate_policy="convert_nearest",
                bit_depth_policy="convert",
            )
            assert reject_no_consent.action == RepairAction.REJECT, (
                f"[decision] no-consent {case.filename}"
            )
        elif case.expected_action == "REQUIRES_CONVERSION_OR_REJECT":
            assert decision.action == RepairAction.REJECT, (
                f"[decision reject-policy] {case.filename}"
            )
            downmix_decision = decide_repair_action(
                metadata,
                profile_name="preserve_supported_rate",
                allow_conversion=True,
                multichannel_policy="downmix",
                sample_rate_policy="convert_nearest",
                bit_depth_policy="convert",
            )
            assert downmix_decision.action == RepairAction.CONVERT, (
                f"[decision downmix] {case.filename}"
            )
        elif case.expected_action == "SHOULD_REJECT":
            assert decision.action == RepairAction.REJECT, f"[decision] {case.filename}"
        else:
            raise AssertionError(f"Unknown expected_action: {case.expected_action}")


def _assert_planning(cases: list[ManifestCase]) -> None:
    # Ensure dedupe preserves folder context and _clean planning works as expected.
    stereo_file = WAVS_DIR / "pcm/pcm_stereo_44100_24.wav"
    pcm_folder = WAVS_DIR / "pcm"
    specs = scan_input_specs([stereo_file, pcm_folder])
    by_path = {spec.path: spec for spec in specs}
    assert stereo_file in by_path, "[planning] expected stereo file in scanned specs"
    assert by_path[stereo_file].source_root == pcm_folder, (
        "[planning] expected folder-root context preference"
    )

    with tempfile.TemporaryDirectory(prefix="wavfix_suite_plan_") as tmp:
        out = Path(tmp)
        ctx = OutputPlanContext(
            output_dir=out,
            overwrite_policy="no",
            existing_items={"pcm_stereo_44100_24.wav", "pcm"},
        )
        direct_spec = InputFileSpec(path=stereo_file, source_root=None)
        root_spec = InputFileSpec(path=stereo_file, source_root=pcm_folder)
        direct_target = plan_output_path(direct_spec, ctx)
        root_target = plan_output_path(root_spec, ctx)
        assert direct_target.name.startswith("pcm_stereo_44100_24_clean"), (
            "[planning] direct _clean expected"
        )
        assert root_target.parent.name.startswith("pcm_clean"), (
            "[planning] root alias _clean expected"
        )


def _assert_processing(cases: list[ManifestCase]) -> None:
    input_paths = [BASE_DIR / case.path for case in cases]
    with tempfile.TemporaryDirectory(prefix="wavfix_suite_proc_") as tmp:
        output_dir = Path(tmp)
        result = process_request(
            request=ProcessRequest(
                output_dir=output_dir,
                input_paths=input_paths,
                overwrite_policy="yes",
                allow_conversion=False,
                profile="preserve_supported_rate",
                multichannel_policy="reject",
                metadata_policy="best_effort",
                sample_rate_policy="convert_nearest",
                bit_depth_policy="convert",
                performance_mode="conservative",
            ),
            max_workers=4,
        )

        expected_rejected = sum(
            1
            for case in cases
            if case.expected_action
            in {"REQUIRES_CONVERSION", "REQUIRES_CONVERSION_OR_REJECT", "SHOULD_REJECT"}
        )
        assert result.rejected == expected_rejected, "[processing] rejected count mismatch"

        for case in cases:
            out_path = output_dir / Path(case.path).name
            if case.expected_action in {"SHOULD_PASS", "SAFE_HEADER_FIX"}:
                assert out_path.exists(), f"[processing] expected output missing: {case.filename}"
            else:
                assert not out_path.exists(), (
                    f"[processing] unexpected output for rejected case: {case.filename}"
                )


def _assert_conversion_processing(cases: list[ManifestCase]) -> None:
    backend_ready = all(
        importlib.util.find_spec(module_name) is not None
        for module_name in ("numpy", "soundfile", "soxr")
    )
    if not backend_ready:
        print("[skip] Conversion backend not installed; conversion processing check skipped.")
        return

    conversion_cases = [
        case
        for case in cases
        if case.expected_action in {"REQUIRES_CONVERSION", "REQUIRES_CONVERSION_OR_REJECT"}
    ]
    input_paths = [BASE_DIR / case.path for case in conversion_cases]
    with tempfile.TemporaryDirectory(prefix="wavfix_suite_conv_") as tmp:
        output_dir = Path(tmp)
        result = process_request(
            request=ProcessRequest(
                output_dir=output_dir,
                input_paths=input_paths,
                overwrite_policy="yes",
                allow_conversion=True,
                profile="preserve_supported_rate",
                multichannel_policy="downmix",
                metadata_policy="best_effort",
                sample_rate_policy="convert_nearest",
                bit_depth_policy="convert",
                performance_mode="balanced",
            ),
            max_workers=4,
        )

        assert result.converted == len(conversion_cases), (
            "[processing-conversion] converted count mismatch"
        )
        for case in conversion_cases:
            out_path = output_dir / Path(case.path).name
            assert out_path.exists(), (
                f"[processing-conversion] expected output missing: {case.filename}"
            )
            out_meta = parse_wav_file(out_path)
            assert out_meta.format_tag == 0x0001, (
                f"[processing-conversion] output not PCM: {case.filename}"
            )


def run(*, regen: bool) -> None:
    if regen or not MANIFEST_PATH.exists():
        generated = generate()
        print(f"Generated {len(generated)} WAV fixture entries.")

    cases = _load_manifest()
    if not cases:
        raise AssertionError("Manifest is empty.")

    _assert_parser(cases)
    print(f"[ok] parser checks: {len(cases)} cases")

    _assert_decisions(cases)
    print(f"[ok] decision checks: {len(cases)} cases")

    _assert_planning(cases)
    print("[ok] planner checks")

    _assert_processing(cases)
    print("[ok] processing checks (no conversion)")

    _assert_conversion_processing(cases)
    print("[ok] conversion processing checks")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run WavFix WAV test suite.")
    parser.add_argument(
        "--regen",
        action="store_true",
        help="Regenerate WAV fixtures and manifest before running checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run(regen=args.regen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
