"""Persistent application settings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from appdirs import user_config_dir


@dataclass(slots=True)
class UISettings:
    dark_mode: bool = True
    performance_mode: Literal["conservative", "balanced", "fast"] = "balanced"
    profile: Literal["preserve_supported_rate", "universal_pioneer_safe"] = (
        "preserve_supported_rate"
    )
    multichannel_policy: Literal["reject", "downmix"] = "downmix"
    metadata_policy: Literal["best_effort", "strict_preserve"] = "best_effort"
    sample_rate_policy: Literal["convert_nearest", "reject_unsupported"] = "convert_nearest"
    bit_depth_policy: Literal["convert", "reject_unsupported"] = "convert"
    converter_backend: Literal["builtin", "ffmpeg"] = "builtin"
    ffmpeg_path: str = ""
    conversion_warning_choice: Literal["ask", "allow", "reject"] = "ask"
    show_ffmpeg_recommendation: bool = True
    check_for_updates: bool = True
    skipped_update_version: str = ""
    last_update_check: int = 0


def _config_file() -> Path:
    config_dir = Path(user_config_dir("WavFix", "Auragami"))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def save_settings(settings: UISettings) -> None:
    config_path = _config_file()
    payload = {
        "DARK_MODE": settings.dark_mode,
        "PERFORMANCE_MODE": settings.performance_mode,
        "PROFILE": settings.profile,
        "MULTICHANNEL_POLICY": settings.multichannel_policy,
        "METADATA_POLICY": settings.metadata_policy,
        "SAMPLE_RATE_POLICY": settings.sample_rate_policy,
        "BIT_DEPTH_POLICY": settings.bit_depth_policy,
        "CONVERTER_BACKEND": settings.converter_backend,
        "FFMPEG_PATH": settings.ffmpeg_path,
        "CONVERSION_WARNING_CHOICE": settings.conversion_warning_choice,
        "SHOW_FFMPEG_RECOMMENDATION": settings.show_ffmpeg_recommendation,
        "CHECK_FOR_UPDATES": settings.check_for_updates,
        "SKIPPED_UPDATE_VERSION": settings.skipped_update_version,
        "LAST_UPDATE_CHECK": settings.last_update_check,
    }
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def load_settings() -> UISettings:
    config_path = _config_file()
    if not config_path.exists():
        settings = UISettings()
        save_settings(settings)
        return settings

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        settings = UISettings()
        save_settings(settings)
        return settings

    performance_mode = str(payload.get("PERFORMANCE_MODE", "balanced")).lower()
    if performance_mode not in {"conservative", "balanced", "fast"}:
        performance_mode = "balanced"
    profile = str(payload.get("PROFILE", "preserve_supported_rate")).lower()
    if profile not in {"preserve_supported_rate", "universal_pioneer_safe"}:
        profile = "preserve_supported_rate"
    multichannel_policy = str(payload.get("MULTICHANNEL_POLICY", "downmix")).lower()
    if multichannel_policy not in {"reject", "downmix"}:
        multichannel_policy = "downmix"
    metadata_policy = str(payload.get("METADATA_POLICY", "best_effort")).lower()
    if metadata_policy not in {"best_effort", "strict_preserve"}:
        metadata_policy = "best_effort"
    sample_rate_policy = str(payload.get("SAMPLE_RATE_POLICY", "convert_nearest")).lower()
    if sample_rate_policy not in {"convert_nearest", "reject_unsupported"}:
        sample_rate_policy = "convert_nearest"
    bit_depth_policy = str(payload.get("BIT_DEPTH_POLICY", "convert")).lower()
    if bit_depth_policy not in {"convert", "reject_unsupported"}:
        bit_depth_policy = "convert"
    converter_backend = str(payload.get("CONVERTER_BACKEND", "builtin")).lower()
    if converter_backend not in {"builtin", "ffmpeg"}:
        converter_backend = "builtin"
    ffmpeg_path = str(payload.get("FFMPEG_PATH", ""))
    conversion_warning_choice = str(payload.get("CONVERSION_WARNING_CHOICE", "ask")).lower()
    if conversion_warning_choice not in {"ask", "allow", "reject"}:
        conversion_warning_choice = "ask"

    return UISettings(
        dark_mode=bool(payload.get("DARK_MODE", True)),
        performance_mode=cast(Literal["conservative", "balanced", "fast"], performance_mode),
        profile=cast(Literal["preserve_supported_rate", "universal_pioneer_safe"], profile),
        multichannel_policy=cast(Literal["reject", "downmix"], multichannel_policy),
        metadata_policy=cast(Literal["best_effort", "strict_preserve"], metadata_policy),
        sample_rate_policy=cast(
            Literal["convert_nearest", "reject_unsupported"],
            sample_rate_policy,
        ),
        bit_depth_policy=cast(
            Literal["convert", "reject_unsupported"],
            bit_depth_policy,
        ),
        converter_backend=cast(Literal["builtin", "ffmpeg"], converter_backend),
        ffmpeg_path=ffmpeg_path,
        conversion_warning_choice=cast(
            Literal["ask", "allow", "reject"],
            conversion_warning_choice,
        ),
        show_ffmpeg_recommendation=bool(payload.get("SHOW_FFMPEG_RECOMMENDATION", True)),
        check_for_updates=bool(payload.get("CHECK_FOR_UPDATES", True)),
        skipped_update_version=str(payload.get("SKIPPED_UPDATE_VERSION", "")),
        last_update_check=int(payload.get("LAST_UPDATE_CHECK", 0) or 0),
    )
