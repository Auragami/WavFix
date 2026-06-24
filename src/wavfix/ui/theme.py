"""UI theme and persisted UI settings helpers."""

from __future__ import annotations

import platform
from typing import Literal

from ..config import UISettings, load_settings, save_settings
from ..core.models import (
    BitDepthPolicy,
    ConverterBackend,
    MetadataPolicy,
    MultiChannelPolicy,
    ProfileName,
    SampleRatePolicy,
)


class UIConfig:
    """UI configuration class for color themes and styling."""

    os_name = platform.system()
    DARK_MODE: bool = True
    PERFORMANCE_MODE: Literal["conservative", "balanced", "fast"] = "balanced"
    PROFILE: ProfileName = "preserve_supported_rate"
    MULTICHANNEL_POLICY: MultiChannelPolicy = "downmix"
    METADATA_POLICY: MetadataPolicy = "best_effort"
    SAMPLE_RATE_POLICY: SampleRatePolicy = "convert_nearest"
    BIT_DEPTH_POLICY: BitDepthPolicy = "convert"
    CONVERTER_BACKEND: ConverterBackend = "builtin"
    FFMPEG_PATH: str = ""
    CONVERSION_WARNING_CHOICE: Literal["ask", "allow", "reject"] = "ask"
    SHOW_FFMPEG_RECOMMENDATION: bool = True
    CHECK_FOR_UPDATES: bool = True
    SKIPPED_UPDATE_VERSION: str = ""
    LAST_UPDATE_CHECK: int = 0

    @staticmethod
    def load() -> None:
        settings = load_settings()
        UIConfig.DARK_MODE = settings.dark_mode
        UIConfig.PERFORMANCE_MODE = settings.performance_mode
        UIConfig.PROFILE = settings.profile
        UIConfig.MULTICHANNEL_POLICY = settings.multichannel_policy
        UIConfig.METADATA_POLICY = settings.metadata_policy
        UIConfig.SAMPLE_RATE_POLICY = settings.sample_rate_policy
        UIConfig.BIT_DEPTH_POLICY = settings.bit_depth_policy
        UIConfig.CONVERTER_BACKEND = settings.converter_backend
        UIConfig.FFMPEG_PATH = settings.ffmpeg_path
        UIConfig.CONVERSION_WARNING_CHOICE = settings.conversion_warning_choice
        UIConfig.SHOW_FFMPEG_RECOMMENDATION = settings.show_ffmpeg_recommendation
        UIConfig.CHECK_FOR_UPDATES = settings.check_for_updates
        UIConfig.SKIPPED_UPDATE_VERSION = settings.skipped_update_version
        UIConfig.LAST_UPDATE_CHECK = settings.last_update_check

    @staticmethod
    def save() -> None:
        save_settings(
            UISettings(
                dark_mode=UIConfig.DARK_MODE,
                performance_mode=UIConfig.PERFORMANCE_MODE,
                profile=UIConfig.PROFILE,
                multichannel_policy=UIConfig.MULTICHANNEL_POLICY,
                metadata_policy=UIConfig.METADATA_POLICY,
                sample_rate_policy=UIConfig.SAMPLE_RATE_POLICY,
                bit_depth_policy=UIConfig.BIT_DEPTH_POLICY,
                converter_backend=UIConfig.CONVERTER_BACKEND,
                ffmpeg_path=UIConfig.FFMPEG_PATH,
                conversion_warning_choice=UIConfig.CONVERSION_WARNING_CHOICE,
                show_ffmpeg_recommendation=UIConfig.SHOW_FFMPEG_RECOMMENDATION,
                check_for_updates=UIConfig.CHECK_FOR_UPDATES,
                skipped_update_version=UIConfig.SKIPPED_UPDATE_VERSION,
                last_update_check=UIConfig.LAST_UPDATE_CHECK,
            )
        )

    @staticmethod
    def bg_color() -> str:
        return "#191919" if UIConfig.DARK_MODE else "#E0E0E0"

    @staticmethod
    def accent_color() -> str:
        return "#9F9F9F" if UIConfig.DARK_MODE else "#333333"

    @staticmethod
    def window_color() -> str:
        return "#0F0F0F" if UIConfig.DARK_MODE else "#2E2E2E"

    @staticmethod
    def header_text_color() -> str:
        return "#9F9F9F" if UIConfig.DARK_MODE else "white"

    @staticmethod
    def button_color() -> str:
        return "#373737" if UIConfig.DARK_MODE else "#5D5D5D"

    @staticmethod
    def button_text_color() -> str:
        return "#EBEBEB" if UIConfig.DARK_MODE else "white"

    @staticmethod
    def hover_color() -> str:
        return "#656565" if UIConfig.DARK_MODE else "#7D7D7D"

    @staticmethod
    def blue_files_color() -> str:
        return "#1876D0" if UIConfig.DARK_MODE else "#3A9BFF"

    @staticmethod
    def green_files_color() -> str:
        return "#17C854" if UIConfig.DARK_MODE else "#3AFF7C"

    @staticmethod
    def success_dialog_color() -> str:
        return UIConfig.green_files_color() if UIConfig.DARK_MODE else "#168A3A"

    @staticmethod
    def red_files_color() -> str:
        return "#C81919" if UIConfig.DARK_MODE else "#FF3A3A"

    @staticmethod
    def yellow_files_color() -> str:
        return "#C8AF18" if UIConfig.DARK_MODE else "#FFE53A"

    @staticmethod
    def orange_files_color() -> str:
        return "#C86918" if UIConfig.DARK_MODE else "#FF963A"

    @staticmethod
    def neutral_files_color() -> str:
        return UIConfig.blue_files_color()

    @staticmethod
    def header_text() -> tuple[str, int, str]:
        size = 12 if UIConfig.os_name == "Darwin" else 9
        return ("Roboto", size, "bold")

    @staticmethod
    def treeview_text() -> tuple[str, int, str]:
        size = 14 if UIConfig.os_name == "Darwin" else 11
        return ("Roboto", size, "normal")

    @staticmethod
    def output_text_color() -> str:
        return UIConfig.header_text_color() if UIConfig.DARK_MODE else UIConfig.button_text_color()

    @staticmethod
    def output_font() -> tuple[str, int]:
        if UIConfig.os_name == "Darwin":
            return ("Menlo", 11)
        if UIConfig.os_name == "Windows":
            return ("Consolas", 12)
        return ("DejaVu Sans Mono", 12)

    @staticmethod
    def output_window_height() -> int:
        return 80 if UIConfig.os_name == "Darwin" else 86

    @staticmethod
    def button_width() -> int:
        return 140

    @staticmethod
    def segmented_palette() -> dict[str, str]:
        if UIConfig.DARK_MODE:
            return {
                "fg_color": UIConfig.window_color(),
                "selected_color": UIConfig.accent_color(),
                "selected_hover_color": UIConfig.hover_color(),
                "unselected_color": UIConfig.button_color(),
                "unselected_hover_color": UIConfig.window_color(),
                "text_color": UIConfig.button_text_color(),
                "border_color": UIConfig.accent_color(),
            }
        return {
            "fg_color": UIConfig.window_color(),
            "selected_color": UIConfig.button_color(),
            "selected_hover_color": UIConfig.hover_color(),
            "unselected_color": UIConfig.accent_color(),
            "unselected_hover_color": UIConfig.button_color(),
            "text_color": UIConfig.button_text_color(),
            "border_color": UIConfig.accent_color(),
        }
