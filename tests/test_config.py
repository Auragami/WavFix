from __future__ import annotations

from pathlib import Path

import wavfix.config.settings as settings_module
from wavfix.config import load_settings, save_settings
from wavfix.config.settings import UISettings


def test_config_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings_module, "user_config_dir", lambda *_: str(tmp_path))

    save_settings(
        UISettings(
            dark_mode=False,
            performance_mode="fast",
            profile="universal_pioneer_safe",
            multichannel_policy="downmix",
            metadata_policy="strict_preserve",
            sample_rate_policy="reject_unsupported",
            bit_depth_policy="reject_unsupported",
            converter_backend="ffmpeg",
            ffmpeg_path="/usr/local/bin/ffmpeg",
            conversion_warning_choice="allow",
            show_ffmpeg_recommendation=False,
            check_for_updates=False,
            skipped_update_version="2.0.1",
            last_update_check=123456,
        )
    )
    loaded = load_settings()
    assert loaded.dark_mode is False
    assert loaded.performance_mode == "fast"
    assert loaded.profile == "universal_pioneer_safe"
    assert loaded.multichannel_policy == "downmix"
    assert loaded.metadata_policy == "strict_preserve"
    assert loaded.sample_rate_policy == "reject_unsupported"
    assert loaded.bit_depth_policy == "reject_unsupported"
    assert loaded.converter_backend == "ffmpeg"
    assert loaded.ffmpeg_path == "/usr/local/bin/ffmpeg"
    assert loaded.conversion_warning_choice == "allow"
    assert loaded.show_ffmpeg_recommendation is False
    assert loaded.check_for_updates is False
    assert loaded.skipped_update_version == "2.0.1"
    assert loaded.last_update_check == 123456


def test_config_defaults_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings_module, "user_config_dir", lambda *_: str(tmp_path))

    loaded = load_settings()
    assert loaded.dark_mode is True
    assert loaded.performance_mode == "balanced"
    assert loaded.profile == "preserve_supported_rate"
    assert loaded.multichannel_policy == "downmix"
    assert loaded.metadata_policy == "best_effort"
    assert loaded.sample_rate_policy == "convert_nearest"
    assert loaded.bit_depth_policy == "convert"
    assert loaded.converter_backend == "builtin"
    assert loaded.ffmpeg_path == ""
    assert loaded.conversion_warning_choice == "ask"
    assert loaded.show_ffmpeg_recommendation is True
    assert loaded.check_for_updates is True
    assert loaded.skipped_update_version == ""
    assert loaded.last_update_check == 0
    assert (tmp_path / "config.json").exists()


def test_config_backward_compat_missing_performance_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings_module, "user_config_dir", lambda *_: str(tmp_path))
    config_file = tmp_path / "config.json"
    config_file.write_text('{"DARK_MODE": false}', encoding="utf-8")

    loaded = load_settings()
    assert loaded.dark_mode is False
    assert loaded.performance_mode == "balanced"
    assert loaded.profile == "preserve_supported_rate"
    assert loaded.multichannel_policy == "downmix"
    assert loaded.metadata_policy == "best_effort"
    assert loaded.sample_rate_policy == "convert_nearest"
    assert loaded.bit_depth_policy == "convert"
    assert loaded.converter_backend == "builtin"
    assert loaded.ffmpeg_path == ""
    assert loaded.conversion_warning_choice == "ask"
    assert loaded.show_ffmpeg_recommendation is True
    assert loaded.check_for_updates is True
    assert loaded.skipped_update_version == ""
    assert loaded.last_update_check == 0
