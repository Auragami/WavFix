"""Deterministic processing decisions based on parsed WAV metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import COMPATIBILITY_PROFILES, SUPPORTED_PCM_BIT_DEPTHS, CompatibilityProfile
from .models import (
    BitDepthPolicy,
    MultiChannelPolicy,
    RepairAction,
    SampleRatePolicy,
    WavFormatKind,
    WavMetadata,
)


@dataclass(slots=True)
class ConversionTarget:
    sample_rate: int
    channels: int
    bit_depth: int


@dataclass(slots=True)
class DecisionOutcome:
    action: RepairAction
    reason: str
    warnings: list[str] = field(default_factory=list)
    target: ConversionTarget | None = None


def _profile(name: str) -> CompatibilityProfile:
    return COMPATIBILITY_PROFILES.get(name, COMPATIBILITY_PROFILES["preserve_supported_rate"])


def _nearest_supported_rate(rate: int, supported: frozenset[int]) -> int:
    ordered = sorted(supported)
    best = ordered[0]
    best_distance = abs(best - rate)
    for candidate in ordered[1:]:
        distance = abs(candidate - rate)
        if distance < best_distance:
            best = candidate
            best_distance = distance
            continue
        if distance == best_distance and candidate < best:
            best = candidate
    return best


def decide_repair_action(
    metadata: WavMetadata,
    *,
    profile_name: str,
    allow_conversion: bool,
    multichannel_policy: MultiChannelPolicy,
    sample_rate_policy: SampleRatePolicy = "convert_nearest",
    bit_depth_policy: BitDepthPolicy = "convert",
) -> DecisionOutcome:
    profile = _profile(profile_name)

    if not metadata.riff_valid or not metadata.wave_valid:
        return DecisionOutcome(RepairAction.REJECT, "Invalid RIFF/WAVE file.")
    if metadata.format_kind == WavFormatKind.MALFORMED:
        return DecisionOutcome(
            RepairAction.REJECT,
            metadata.parse_error or "Malformed WAV; unsafe to process.",
        )
    if metadata.format_kind in {
        WavFormatKind.UNSUPPORTED,
        WavFormatKind.EXTENSIBLE_UNSUPPORTED,
    }:
        return DecisionOutcome(RepairAction.REJECT, "Unsupported WAV format/subtype.")

    channels = metadata.channels
    sample_rate = metadata.sample_rate
    bits = metadata.bits_per_sample
    if channels is None or sample_rate is None or bits is None:
        return DecisionOutcome(RepairAction.REJECT, "Incomplete WAV metadata.")

    conversion_reasons: list[str] = []
    reject_reasons: list[str] = []
    requires_float_conversion = metadata.format_kind in {
        WavFormatKind.IEEE_FLOAT,
        WavFormatKind.EXTENSIBLE_FLOAT,
    }
    channels_need_conversion = False
    sample_rate_need_conversion = False
    bit_depth_need_conversion = False

    if requires_float_conversion:
        conversion_reasons.append("Float WAV requires true conversion to PCM.")

    if channels not in profile.allowed_channels:
        if channels > 2:
            if multichannel_policy == "downmix":
                channels_need_conversion = True
                conversion_reasons.append("Multichannel audio requires stereo downmix.")
            else:
                reject_reasons.append("Multichannel input is disabled by policy.")
        else:
            reject_reasons.append("Channel count is incompatible with selected profile.")

    if sample_rate not in profile.supported_sample_rates:
        if sample_rate_policy == "reject_unsupported":
            reject_reasons.append(
                "Sample rate is unsupported and sample-rate policy is set to reject."
            )
        else:
            sample_rate_need_conversion = True
            nearest_rate = _nearest_supported_rate(sample_rate, profile.supported_sample_rates)
            conversion_reasons.append(
                "Sample rate "
                f"{sample_rate} Hz is unsupported; converting to nearest supported rate "
                f"{nearest_rate} Hz."
            )

    if bits not in SUPPORTED_PCM_BIT_DEPTHS:
        if bit_depth_policy == "reject_unsupported":
            reject_reasons.append("Bit depth is unsupported and bit-depth policy is set to reject.")
        else:
            bit_depth_need_conversion = True
            conversion_reasons.append("Bit depth requires conversion to 24-bit PCM.")

    if reject_reasons:
        return DecisionOutcome(
            RepairAction.REJECT,
            "; ".join(reject_reasons),
        )

    if conversion_reasons or requires_float_conversion or channels_need_conversion:
        target_channels = channels
        if channels_need_conversion:
            target_channels = 2
        if sample_rate_need_conversion:
            target_rate = _nearest_supported_rate(sample_rate, profile.supported_sample_rates)
        elif sample_rate in profile.supported_sample_rates:
            target_rate = sample_rate
        else:
            target_rate = profile.preferred_sample_rate
        if requires_float_conversion or bit_depth_need_conversion:
            target_depth = profile.preferred_bit_depth
        elif bits in SUPPORTED_PCM_BIT_DEPTHS:
            target_depth = bits
        else:
            target_depth = profile.preferred_bit_depth
        target = ConversionTarget(
            sample_rate=target_rate,
            channels=target_channels,
            bit_depth=target_depth,
        )

        if not allow_conversion:
            return DecisionOutcome(
                RepairAction.REJECT,
                "Conversion required but conversion consent is not enabled.",
                target=target,
            )

        return DecisionOutcome(
            RepairAction.CONVERT,
            "; ".join(conversion_reasons),
            target=target,
        )

    if metadata.format_kind == WavFormatKind.EXTENSIBLE_PCM:
        return DecisionOutcome(
            RepairAction.HEADER_FIX,
            "Extensible PCM is profile-compatible; normalizing header to canonical PCM.",
        )

    if metadata.format_kind == WavFormatKind.PCM:
        return DecisionOutcome(RepairAction.PASS_THROUGH, "Already Pioneer-compatible PCM.")

    return DecisionOutcome(RepairAction.REJECT, "Unsupported or ambiguous WAV classification.")
