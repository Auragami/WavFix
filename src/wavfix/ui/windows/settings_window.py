"""Settings window builder/controller for the WavFix UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkfont
from typing import Literal, cast

from customtkinter import CTkButton, CTkFrame, CTkLabel, CTkScrollableFrame

from ...core.models import (
    BitDepthPolicy,
    ConverterBackend,
    MetadataPolicy,
    MultiChannelPolicy,
    ProfileName,
    SampleRatePolicy,
)
from ..behaviors.tooltip import ToolTip
from ..theme import UIConfig
from ..widgets.segmented_control import SegmentedControl


class SettingsWindow:
    """Owns Settings UI state and persistence behavior."""

    _BASE_CONTENT_WIDTH = 340

    _PROFILE_LABEL_BY_VALUE: dict[ProfileName, str] = {
        "preserve_supported_rate": "Balanced",
        "universal_pioneer_safe": "Strict",
    }
    _PROFILE_VALUE_BY_LABEL: dict[str, ProfileName] = {
        "Balanced": "preserve_supported_rate",
        "Strict": "universal_pioneer_safe",
    }
    _MULTICHANNEL_LABEL_BY_VALUE: dict[MultiChannelPolicy, str] = {
        "downmix": "Downmix",
        "reject": "Reject",
    }
    _MULTICHANNEL_VALUE_BY_LABEL: dict[str, MultiChannelPolicy] = {
        "Downmix": "downmix",
        "Reject": "reject",
    }
    _METADATA_LABEL_BY_VALUE: dict[MetadataPolicy, str] = {
        "best_effort": "Best Effort",
        "strict_preserve": "Strict Preserve",
    }
    _METADATA_VALUE_BY_LABEL: dict[str, MetadataPolicy] = {
        "Best Effort": "best_effort",
        "Strict Preserve": "strict_preserve",
    }
    _SAMPLE_RATE_LABEL_BY_VALUE: dict[SampleRatePolicy, str] = {
        "convert_nearest": "Convert",
        "reject_unsupported": "Reject",
    }
    _SAMPLE_RATE_VALUE_BY_LABEL: dict[str, SampleRatePolicy] = {
        "Convert": "convert_nearest",
        "Reject": "reject_unsupported",
    }
    _BIT_DEPTH_LABEL_BY_VALUE: dict[BitDepthPolicy, str] = {
        "convert": "Convert",
        "reject_unsupported": "Reject",
    }
    _BIT_DEPTH_VALUE_BY_LABEL: dict[str, BitDepthPolicy] = {
        "Convert": "convert",
        "Reject": "reject_unsupported",
    }
    _CONVERTER_LABEL_BY_VALUE: dict[ConverterBackend, str] = {
        "builtin": "Built-in",
        "ffmpeg": "FFmpeg",
    }
    _CONVERTER_VALUE_BY_LABEL: dict[str, ConverterBackend] = {
        "Built-in": "builtin",
        "FFmpeg": "ffmpeg",
    }
    _THEME_TOOLTIPS: dict[str, str] = {
        "Dark": "Use dark UI theme across the app.",
        "Light": "Use light UI theme across the app.",
    }
    _PERFORMANCE_TOOLTIPS: dict[str, str] = {
        "Conservative": "Lowest resource usage; slowest processing.",
        "Balanced": "Balanced speed and system load.",
        "Fast": "Highest throughput with higher system load.",
    }
    _UPDATE_TOOLTIPS: dict[str, str] = {
        "On": "Check GitHub Releases periodically and notify you when a new version is available.",
        "Off": "Do not check for WavFix updates automatically.",
    }
    _PROFILE_TOOLTIPS: dict[str, str] = {
        "Balanced": "Lower strictness: allows supported rates and mono/stereo when compatible.",
        "Strict": "Higher strictness: targets universal-safe 44.1 kHz stereo behavior.",
    }
    _MULTICHANNEL_TOOLTIPS: dict[str, str] = {
        "Downmix": "Allow stereo downmix when channels exceed compatibility.",
        "Reject": "Reject files that require multichannel conversion.",
    }
    _METADATA_TOOLTIPS: dict[str, str] = {
        "Best Effort": (
            "Preserve common metadata when practical; unsupported chunks "
            "may be dropped with warnings."
        ),
        "Strict Preserve": "Reject conversion if metadata cannot be fully preserved by policy.",
    }
    _SAMPLE_RATE_TOOLTIPS: dict[str, str] = {
        "Convert": "Unsupported sample rates are converted to the nearest supported rate.",
        "Reject": "Unsupported sample rates are skipped.",
    }
    _BIT_DEPTH_TOOLTIPS: dict[str, str] = {
        "Convert": "Unsupported bit depths are converted to 24-bit PCM.",
        "Reject": "Unsupported bit depths are skipped.",
    }
    _CONVERTER_TOOLTIPS: dict[str, str] = {
        "Built-in": "Use WavFix's bundled SoundFile + SoXR converter. Recommended default.",
        "FFmpeg": "Use a free external FFmpeg executable for conversion when configured.",
    }

    def __init__(
        self,
        root: tk.Tk,
        *,
        on_theme_preview,
        on_refresh_status,
        on_check_updates,
    ) -> None:
        self.root = root
        self.on_theme_preview = on_theme_preview
        self.on_refresh_status = on_refresh_status
        self.on_check_updates = on_check_updates

        self.window: tk.Toplevel | None = None
        self.theme_segmented: SegmentedControl | None = None
        self.perf_segmented: SegmentedControl | None = None
        self.update_segmented: SegmentedControl | None = None
        self.check_now_button: CTkButton | None = None
        self.reset_notices_button: CTkButton | None = None
        self.profile_segmented: SegmentedControl | None = None
        self.multichannel_segmented: SegmentedControl | None = None
        self.metadata_segmented: SegmentedControl | None = None
        self.sample_rate_segmented: SegmentedControl | None = None
        self.bit_depth_segmented: SegmentedControl | None = None
        self.converter_segmented: SegmentedControl | None = None
        self.ffmpeg_path_var = tk.StringVar(value="")
        self.ffmpeg_path_label: CTkLabel | None = None
        self.ffmpeg_choose_button: CTkButton | None = None
        self.ffmpeg_auto_button: CTkButton | None = None
        self.advanced_toggle_button: CTkButton | None = None
        self.refresh_button: CTkButton | None = None
        self.cancel_button: CTkButton | None = None
        self.save_button: CTkButton | None = None
        self.general_panel: CTkFrame | None = None
        self.advanced_panel: CTkFrame | None = None
        self.advanced_content_panel: CTkScrollableFrame | None = None
        self.initial_dark_mode: bool | None = None
        self.advanced_expanded = False
        self._reset_notice_preferences_requested = False
        self._window_anchor: tuple[int, int] | None = None
        self.tooltips: list[ToolTip] = []

    def open(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_set()
            return

        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.title("Settings")
        self.window.transient(self.root)
        self.window.resizable(False, False)
        self.window.configure(bg=UIConfig.window_color())
        self.window.grid_columnconfigure(0, weight=1)
        self.initial_dark_mode = UIConfig.DARK_MODE
        self.advanced_expanded = False
        self._reset_notice_preferences_requested = False
        segmented_width = self._settings_segmented_width()

        self.general_panel = CTkFrame(
            master=self.window,
            fg_color=UIConfig.bg_color(),
            border_color=UIConfig.accent_color(),
            border_width=1,
            corner_radius=10,
        )
        self.general_panel.grid(row=0, column=0, sticky="we", padx=12, pady=(12, 8))
        self.general_panel.grid_columnconfigure(0, weight=1)

        theme_label = CTkLabel(
            master=self.general_panel,
            text="Theme",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        theme_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        self.theme_segmented = SegmentedControl(
            master=self.general_panel,
            values=["Dark", "Light"],
            width=segmented_width,
            command=self._on_theme_changed,
        )
        self.theme_segmented.grid(row=1, column=0, sticky="we", padx=10, pady=(0, 10))
        self.theme_segmented.set("Dark" if UIConfig.DARK_MODE else "Light")

        perf_label = CTkLabel(
            master=self.general_panel,
            text="Performance",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        perf_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 4))

        self.perf_segmented = SegmentedControl(
            master=self.general_panel,
            values=["Conservative", "Balanced", "Fast"],
            width=segmented_width,
        )
        self.perf_segmented.grid(row=3, column=0, sticky="we", padx=10, pady=(0, 10))
        perf_map = {
            "conservative": "Conservative",
            "balanced": "Balanced",
            "fast": "Fast",
        }
        self.perf_segmented.set(perf_map.get(UIConfig.PERFORMANCE_MODE, "Balanced"))

        update_label = CTkLabel(
            master=self.general_panel,
            text="Update Alerts",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        update_label.grid(row=4, column=0, sticky="w", padx=10, pady=(0, 4))

        self.update_segmented = SegmentedControl(
            master=self.general_panel,
            values=["On", "Off"],
            width=segmented_width,
        )
        self.update_segmented.grid(row=5, column=0, sticky="we", padx=10, pady=(0, 10))
        self.update_segmented.set("On" if UIConfig.CHECK_FOR_UPDATES else "Off")

        self.check_now_button = CTkButton(
            master=self.general_panel,
            text="Check Now",
            width=segmented_width,
            corner_radius=16,
            command=self._check_now,
            border_width=2,
        )
        self.check_now_button.grid(row=6, column=0, sticky="we", padx=10, pady=(4, 8))

        self.reset_notices_button = CTkButton(
            master=self.general_panel,
            text="Restore Notices",
            width=segmented_width,
            corner_radius=16,
            command=self._request_notice_reset,
            border_width=2,
        )
        self.reset_notices_button.grid(row=7, column=0, sticky="we", padx=10, pady=(4, 12))

        self.advanced_toggle_button = CTkButton(
            master=self.window,
            text=self._advanced_toggle_text(),
            width=segmented_width,
            height=32,
            corner_radius=12,
            font=("Roboto", 11, "bold"),
            command=self._toggle_advanced_section,
            anchor="w",
            border_width=2,
        )
        self.advanced_toggle_button.grid(row=1, column=0, sticky="we", padx=12, pady=(0, 8))

        self.advanced_panel = CTkFrame(
            master=self.window,
            fg_color=UIConfig.bg_color(),
            border_color=UIConfig.accent_color(),
            border_width=1,
            corner_radius=10,
        )
        self.advanced_panel.grid_columnconfigure(0, weight=1)
        self.advanced_panel.grid_rowconfigure(0, weight=1)

        advanced_scroll_width = segmented_width - 20
        self.advanced_content_panel = CTkScrollableFrame(
            master=self.advanced_panel,
            width=advanced_scroll_width,
            height=300,
            fg_color=UIConfig.bg_color(),
            border_width=0,
            corner_radius=8,
            scrollbar_button_color=UIConfig.button_color(),
            scrollbar_button_hover_color=UIConfig.hover_color(),
        )
        self.advanced_content_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 8))
        self.advanced_content_panel.grid_columnconfigure(0, weight=1)
        self.advanced_content_panel.grid_columnconfigure(1, weight=1)

        advanced_control_width = advanced_scroll_width - 24

        profile_label = CTkLabel(
            master=self.advanced_content_panel,
            text="Strictness",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        profile_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 4))
        self.profile_segmented = SegmentedControl(
            master=self.advanced_content_panel,
            values=list(self._PROFILE_VALUE_BY_LABEL.keys()),
            width=advanced_control_width,
        )
        self.profile_segmented.grid(
            row=1, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 10)
        )
        self.profile_segmented.set(self._PROFILE_LABEL_BY_VALUE[UIConfig.PROFILE])

        sample_rate_label = CTkLabel(
            master=self.advanced_content_panel,
            text="Sample Rate",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        sample_rate_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
        self.sample_rate_segmented = SegmentedControl(
            master=self.advanced_content_panel,
            values=list(self._SAMPLE_RATE_VALUE_BY_LABEL.keys()),
            width=advanced_control_width,
        )
        self.sample_rate_segmented.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="we",
            padx=10,
            pady=(0, 10),
        )
        self.sample_rate_segmented.set(
            self._SAMPLE_RATE_LABEL_BY_VALUE[UIConfig.SAMPLE_RATE_POLICY]
        )

        bit_depth_label = CTkLabel(
            master=self.advanced_content_panel,
            text="Bit Depth",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        bit_depth_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
        self.bit_depth_segmented = SegmentedControl(
            master=self.advanced_content_panel,
            values=list(self._BIT_DEPTH_VALUE_BY_LABEL.keys()),
            width=advanced_control_width,
        )
        self.bit_depth_segmented.grid(
            row=5, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 10)
        )
        self.bit_depth_segmented.set(self._BIT_DEPTH_LABEL_BY_VALUE[UIConfig.BIT_DEPTH_POLICY])

        multichannel_label = CTkLabel(
            master=self.advanced_content_panel,
            text="Multichannel",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        multichannel_label.grid(row=6, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
        self.multichannel_segmented = SegmentedControl(
            master=self.advanced_content_panel,
            values=list(self._MULTICHANNEL_VALUE_BY_LABEL.keys()),
            width=advanced_control_width,
        )
        self.multichannel_segmented.grid(
            row=7, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 10)
        )
        self.multichannel_segmented.set(
            self._MULTICHANNEL_LABEL_BY_VALUE[UIConfig.MULTICHANNEL_POLICY]
        )

        metadata_label = CTkLabel(
            master=self.advanced_content_panel,
            text="Metadata",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        metadata_label.grid(row=8, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
        self.metadata_segmented = SegmentedControl(
            master=self.advanced_content_panel,
            values=list(self._METADATA_VALUE_BY_LABEL.keys()),
            width=advanced_control_width,
        )
        self.metadata_segmented.grid(
            row=9, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 10)
        )
        self.metadata_segmented.set(self._METADATA_LABEL_BY_VALUE[UIConfig.METADATA_POLICY])

        converter_label = CTkLabel(
            master=self.advanced_content_panel,
            text="Converter",
            font=("Roboto", 11, "bold"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
        )
        converter_label.grid(row=10, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
        self.converter_segmented = SegmentedControl(
            master=self.advanced_content_panel,
            values=list(self._CONVERTER_VALUE_BY_LABEL.keys()),
            width=advanced_control_width,
            command=lambda _value: self._refresh_ffmpeg_source_state(),
        )
        self.converter_segmented.grid(
            row=11, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 10)
        )
        self.converter_segmented.set(self._CONVERTER_LABEL_BY_VALUE[UIConfig.CONVERTER_BACKEND])

        self.ffmpeg_path_var.set(UIConfig.FFMPEG_PATH or "Auto-detect from PATH")
        self.ffmpeg_path_label = CTkLabel(
            master=self.advanced_content_panel,
            textvariable=self.ffmpeg_path_var,
            font=("Roboto", 10, "normal"),
            fg_color="transparent",
            text_color=UIConfig.accent_color(),
            anchor="w",
        )
        self.ffmpeg_path_label.grid(
            row=13, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 6)
        )

        self.refresh_button = CTkButton(
            master=self.advanced_panel,
            text="Refresh Status",
            width=advanced_scroll_width,
            corner_radius=16,
            command=self._on_refresh_clicked,
            border_width=2,
        )
        self.refresh_button.grid(row=1, column=0, sticky="we", padx=10, pady=(0, 10))

        self.ffmpeg_choose_button = CTkButton(
            master=self.advanced_content_panel,
            text="Choose FFmpeg",
            corner_radius=14,
            command=self._choose_ffmpeg_path,
            border_width=2,
        )
        self.ffmpeg_choose_button.grid(row=14, column=0, sticky="we", padx=(10, 5), pady=(0, 10))
        self.ffmpeg_auto_button = CTkButton(
            master=self.advanced_content_panel,
            text="Use PATH",
            corner_radius=14,
            command=self._use_auto_ffmpeg_path,
            border_width=2,
        )
        self.ffmpeg_auto_button.grid(row=14, column=1, sticky="we", padx=(5, 10), pady=(0, 10))

        buttons_frame = CTkFrame(master=self.window, fg_color="transparent")
        buttons_frame.grid(row=3, column=0, sticky="we", padx=12, pady=(0, 12))
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        self.cancel_button = CTkButton(
            master=buttons_frame,
            text="Cancel",
            width=90,
            corner_radius=14,
            command=self.close,
            border_width=2,
        )
        self.cancel_button.grid(row=0, column=0, sticky="we", padx=(0, 5))
        self.save_button = CTkButton(
            master=buttons_frame,
            text="Save",
            width=90,
            corner_radius=14,
            command=self._save,
            border_width=2,
        )
        self.save_button.grid(row=0, column=1, sticky="we", padx=(5, 0))

        self._set_advanced_visibility()
        self._apply_segmented_palette(
            self.theme_segmented,
            self.perf_segmented,
            self.update_segmented,
            self.profile_segmented,
            self.multichannel_segmented,
            self.metadata_segmented,
            self.sample_rate_segmented,
            self.bit_depth_segmented,
            self.converter_segmented,
        )
        self._apply_settings_button_styles()
        self._refresh_ffmpeg_source_state()
        self._build_tooltips()

        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._center_window()
        self.window.deiconify()
        self.window.lift()
        self.window.focus_set()

    def close(self, revert_preview: bool = True) -> None:
        if revert_preview and self.initial_dark_mode is not None:
            if UIConfig.DARK_MODE != self.initial_dark_mode:
                UIConfig.DARK_MODE = self.initial_dark_mode
                self.on_theme_preview()
        if self.window is not None and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.theme_segmented = None
        self.perf_segmented = None
        self.update_segmented = None
        self.check_now_button = None
        self.reset_notices_button = None
        self.profile_segmented = None
        self.multichannel_segmented = None
        self.metadata_segmented = None
        self.sample_rate_segmented = None
        self.bit_depth_segmented = None
        self.converter_segmented = None
        self.ffmpeg_path_label = None
        self.ffmpeg_choose_button = None
        self.ffmpeg_auto_button = None
        self.advanced_toggle_button = None
        self.refresh_button = None
        self.cancel_button = None
        self.save_button = None
        self.general_panel = None
        self.advanced_panel = None
        self.advanced_content_panel = None
        self.initial_dark_mode = None
        self.advanced_expanded = False
        self._reset_notice_preferences_requested = False
        self._window_anchor = None
        self.tooltips = []
        try:
            self.root.focus_set()
        except tk.TclError:
            return

    def is_open(self) -> bool:
        return self.window is not None and self.window.winfo_exists()

    def set_busy(self, is_busy: bool) -> None:
        if self.refresh_button is not None:
            self.refresh_button.configure(state="disabled" if is_busy else "normal")
        if self.check_now_button is not None:
            self.check_now_button.configure(state="disabled" if is_busy else "normal")

    def apply_theme_styles(self) -> None:
        if (
            self.window is None
            or not self.window.winfo_exists()
            or self.theme_segmented is None
            or self.perf_segmented is None
            or self.update_segmented is None
            or self.profile_segmented is None
            or self.multichannel_segmented is None
            or self.metadata_segmented is None
            or self.sample_rate_segmented is None
            or self.bit_depth_segmented is None
            or self.converter_segmented is None
        ):
            return

        self.window.configure(bg=UIConfig.window_color())
        if self.general_panel is not None:
            self.general_panel.configure(
                fg_color=UIConfig.bg_color(),
                border_color=UIConfig.accent_color(),
            )
        if self.advanced_panel is not None:
            self.advanced_panel.configure(
                fg_color=UIConfig.bg_color(),
                border_color=UIConfig.accent_color(),
            )
        if self.advanced_content_panel is not None:
            self.advanced_content_panel.configure(
                fg_color=UIConfig.bg_color(),
                scrollbar_button_color=UIConfig.button_color(),
                scrollbar_button_hover_color=UIConfig.hover_color(),
            )
        self._apply_label_theme(self.window)
        self._apply_segmented_palette(
            self.theme_segmented,
            self.perf_segmented,
            self.update_segmented,
            self.profile_segmented,
            self.multichannel_segmented,
            self.metadata_segmented,
            self.sample_rate_segmented,
            self.bit_depth_segmented,
            self.converter_segmented,
        )
        self._apply_settings_button_styles()
        self._refresh_ffmpeg_source_state()

    def _settings_segmented_width(self) -> int:
        labels = [
            "Dark",
            "Light",
            "Conservative",
            "Balanced",
            "Fast",
            "Updates",
            "Check Now",
            "Restore Notices",
            "Strict",
            "Downmix",
            "Convert",
            "Reject",
            "Best Effort",
            "Strict Preserve",
            "Choose FFmpeg",
            "Auto-detect from PATH",
            "Processing Options",
        ]
        measure_font = tkfont.Font(family="Roboto", size=11, weight="bold")
        max_text = max(measure_font.measure(label) for label in labels)
        return max(self._BASE_CONTENT_WIDTH, max_text + 64)

    def _center_window(self, *, preserve_position: bool = False) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        self.root.update_idletasks()
        if preserve_position and self._window_anchor is not None:
            anchor = self._window_anchor
            self.window.geometry(f"+{anchor[0]}+{anchor[1]}")
        self.window.update_idletasks()

        window_width = self.window.winfo_reqwidth()
        window_height = self.window.winfo_reqheight()
        if preserve_position and self._window_anchor is not None:
            x, y = self._window_anchor
        else:
            parent_x = self.root.winfo_rootx()
            parent_y = self.root.winfo_rooty()
            parent_width = self.root.winfo_width()
            parent_height = self.root.winfo_height()
            x = parent_x + max(0, (parent_width - window_width) // 2)
            y = parent_y + max(0, (parent_height - window_height) // 2)
            self._window_anchor = (x, y)
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _build_tooltips(self) -> None:
        self.tooltips = []
        tooltip_specs: list[tuple[object, str]] = []

        if self.theme_segmented is not None:
            for label, button in self.theme_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._THEME_TOOLTIPS.get(
                            label,
                            "Preview Dark/Light theme instantly. "
                            "Save to keep it, Cancel to revert.",
                        ),
                    )
                )
        if self.perf_segmented is not None:
            for label, button in self.perf_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._PERFORMANCE_TOOLTIPS.get(
                            label,
                            "Processing speed profile. Applies on Save.",
                        ),
                    )
                )
        if self.update_segmented is not None:
            for label, button in self.update_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._UPDATE_TOOLTIPS.get(
                            label,
                            "Control whether WavFix checks GitHub Releases for updates.",
                        ),
                    )
                )
        if self.profile_segmented is not None:
            for label, button in self.profile_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._PROFILE_TOOLTIPS.get(
                            label,
                            "Compatibility target for WAV output behavior.",
                        ),
                    )
                )
        if self.multichannel_segmented is not None:
            for label, button in self.multichannel_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._MULTICHANNEL_TOOLTIPS.get(
                            label,
                            "How multichannel WAV files are handled during processing.",
                        ),
                    )
                )
        if self.metadata_segmented is not None:
            for label, button in self.metadata_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._METADATA_TOOLTIPS.get(
                            label,
                            "Metadata preservation behavior during conversion.",
                        ),
                    )
                )
        if self.sample_rate_segmented is not None:
            for label, button in self.sample_rate_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._SAMPLE_RATE_TOOLTIPS.get(
                            label,
                            "How unsupported sample rates are handled.",
                        ),
                    )
                )
        if self.bit_depth_segmented is not None:
            for label, button in self.bit_depth_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._BIT_DEPTH_TOOLTIPS.get(
                            label,
                            "How unsupported bit depths are handled.",
                        ),
                    )
                )
        if self.converter_segmented is not None:
            for label, button in self.converter_segmented._buttons.items():
                tooltip_specs.append(
                    (
                        button,
                        self._CONVERTER_TOOLTIPS.get(
                            label,
                            "Choose which conversion engine WavFix uses for audio conversion.",
                        ),
                    )
                )
        if self.ffmpeg_path_label is not None:
            tooltip_specs.append(
                (
                    self.ffmpeg_path_label,
                    "FFmpeg is free and optional. Leave blank to auto-detect it from PATH.",
                )
            )
        if self.ffmpeg_choose_button is not None:
            tooltip_specs.append(
                (
                    self.ffmpeg_choose_button,
                    "Choose the FFmpeg executable WavFix should use.",
                )
            )
        if self.ffmpeg_auto_button is not None:
            tooltip_specs.append(
                (
                    self.ffmpeg_auto_button,
                    "Use the FFmpeg executable found on your system PATH.",
                )
            )
        if self.advanced_toggle_button is not None:
            tooltip_specs.append(
                (
                    self.advanced_toggle_button,
                    "Show or hide processing options.",
                )
            )
        if self.refresh_button is not None:
            tooltip_specs.append(
                (
                    self.refresh_button,
                    "Re-check loaded files using current Advanced options.",
                )
            )
        if self.check_now_button is not None:
            tooltip_specs.append(
                (
                    self.check_now_button,
                    "Check GitHub Releases for a newer WavFix version now.",
                )
            )
        if self.reset_notices_button is not None:
            tooltip_specs.append(
                (
                    self.reset_notices_button,
                    "Restore conversion and FFmpeg notices that were hidden "
                    "with do-not-show-again.",
                )
            )
        if self.cancel_button is not None:
            tooltip_specs.append(
                (
                    self.cancel_button,
                    "Close settings without saving Advanced changes.",
                )
            )
        if self.save_button is not None:
            tooltip_specs.append((self.save_button, "Save Advanced settings and close."))

        for widget, text in tooltip_specs:
            self.tooltips.append(ToolTip(widget, text))

    def _on_theme_changed(self, selected_theme: str) -> None:
        dark_mode = selected_theme == "Dark"
        if UIConfig.DARK_MODE == dark_mode:
            return
        UIConfig.DARK_MODE = dark_mode
        self.on_theme_preview()

    def _save(self) -> None:
        if (
            self.theme_segmented is None
            or self.perf_segmented is None
            or self.update_segmented is None
            or self.profile_segmented is None
            or self.multichannel_segmented is None
            or self.metadata_segmented is None
            or self.sample_rate_segmented is None
            or self.bit_depth_segmented is None
            or self.converter_segmented is None
        ):
            return
        selected_theme = self.theme_segmented.get()
        selected_perf = self.perf_segmented.get()
        selected_updates = self.update_segmented.get()
        (
            next_profile,
            next_multichannel_policy,
            next_metadata_policy,
            next_sample_rate_policy,
            next_bit_depth_policy,
            next_converter_backend,
            next_ffmpeg_path,
        ) = self._selected_processing_options()
        processing_options_changed = (
            UIConfig.PROFILE != next_profile
            or UIConfig.MULTICHANNEL_POLICY != next_multichannel_policy
            or UIConfig.METADATA_POLICY != next_metadata_policy
            or UIConfig.SAMPLE_RATE_POLICY != next_sample_rate_policy
            or UIConfig.BIT_DEPTH_POLICY != next_bit_depth_policy
        )

        UIConfig.DARK_MODE = selected_theme == "Dark"
        perf_map = {
            "Conservative": "conservative",
            "Balanced": "balanced",
            "Fast": "fast",
        }
        UIConfig.PERFORMANCE_MODE = cast(
            Literal["conservative", "balanced", "fast"],
            perf_map.get(selected_perf, "balanced"),
        )
        UIConfig.CHECK_FOR_UPDATES = selected_updates == "On"
        UIConfig.PROFILE = next_profile
        UIConfig.MULTICHANNEL_POLICY = next_multichannel_policy
        UIConfig.METADATA_POLICY = next_metadata_policy
        UIConfig.SAMPLE_RATE_POLICY = next_sample_rate_policy
        UIConfig.BIT_DEPTH_POLICY = next_bit_depth_policy
        UIConfig.CONVERTER_BACKEND = next_converter_backend
        UIConfig.FFMPEG_PATH = next_ffmpeg_path
        if self._reset_notice_preferences_requested:
            UIConfig.CONVERSION_WARNING_CHOICE = "ask"
            UIConfig.SHOW_FFMPEG_RECOMMENDATION = True
        UIConfig.save()
        self.on_theme_preview()
        if processing_options_changed:
            self.on_refresh_status(
                (
                    next_profile,
                    next_multichannel_policy,
                    next_metadata_policy,
                    next_sample_rate_policy,
                    next_bit_depth_policy,
                    next_converter_backend,
                    next_ffmpeg_path,
                )
            )
        self.initial_dark_mode = UIConfig.DARK_MODE
        self.close(revert_preview=False)

    def _request_notice_reset(self) -> None:
        self._reset_notice_preferences_requested = True
        if self.reset_notices_button is not None:
            self.reset_notices_button.configure(text="Notices Will Restore")

    def _selected_processing_options(
        self,
    ) -> tuple[
        ProfileName,
        MultiChannelPolicy,
        MetadataPolicy,
        SampleRatePolicy,
        BitDepthPolicy,
        ConverterBackend,
        str,
    ]:
        if (
            self.profile_segmented is None
            or self.multichannel_segmented is None
            or self.metadata_segmented is None
            or self.sample_rate_segmented is None
            or self.bit_depth_segmented is None
            or self.converter_segmented is None
        ):
            return (
                UIConfig.PROFILE,
                UIConfig.MULTICHANNEL_POLICY,
                UIConfig.METADATA_POLICY,
                UIConfig.SAMPLE_RATE_POLICY,
                UIConfig.BIT_DEPTH_POLICY,
                UIConfig.CONVERTER_BACKEND,
                UIConfig.FFMPEG_PATH,
            )
        selected_profile = self.profile_segmented.get()
        selected_multichannel = self.multichannel_segmented.get()
        selected_metadata = self.metadata_segmented.get()
        selected_sample_rate = self.sample_rate_segmented.get()
        selected_bit_depth = self.bit_depth_segmented.get()
        selected_converter = self.converter_segmented.get()
        next_profile = self._PROFILE_VALUE_BY_LABEL.get(
            selected_profile,
            "preserve_supported_rate",
        )
        next_multichannel_policy = self._MULTICHANNEL_VALUE_BY_LABEL.get(
            selected_multichannel,
            "reject",
        )
        next_metadata_policy = self._METADATA_VALUE_BY_LABEL.get(
            selected_metadata,
            "best_effort",
        )
        next_sample_rate_policy = self._SAMPLE_RATE_VALUE_BY_LABEL.get(
            selected_sample_rate,
            "convert_nearest",
        )
        next_bit_depth_policy = self._BIT_DEPTH_VALUE_BY_LABEL.get(
            selected_bit_depth,
            "convert",
        )
        next_converter_backend = self._CONVERTER_VALUE_BY_LABEL.get(
            selected_converter,
            "builtin",
        )
        next_ffmpeg_path = (
            ""
            if self.ffmpeg_path_var.get() == "Auto-detect from PATH"
            else (self.ffmpeg_path_var.get().strip())
        )
        return (
            next_profile,
            next_multichannel_policy,
            next_metadata_policy,
            next_sample_rate_policy,
            next_bit_depth_policy,
            next_converter_backend,
            next_ffmpeg_path,
        )

    def _on_refresh_clicked(self) -> None:
        self.on_refresh_status(self._selected_processing_options())

    def _check_now(self) -> None:
        self.on_check_updates()

    def _choose_ffmpeg_path(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose FFmpeg Executable",
            parent=self.window,
        )
        if selected:
            self.ffmpeg_path_var.set(selected)
            self._refresh_ffmpeg_source_state()

    def _use_auto_ffmpeg_path(self) -> None:
        self.ffmpeg_path_var.set("Auto-detect from PATH")
        self._refresh_ffmpeg_source_state()

    def _refresh_ffmpeg_source_state(self) -> None:
        if self.converter_segmented is None:
            return
        ffmpeg_enabled = self.converter_segmented.get() == "FFmpeg"
        if not self.ffmpeg_path_var.get().strip():
            self.ffmpeg_path_var.set("Auto-detect from PATH")
        state = "normal" if ffmpeg_enabled else "disabled"
        for button in (self.ffmpeg_choose_button, self.ffmpeg_auto_button):
            if button is not None:
                button.configure(state=state)
        if self.ffmpeg_path_label is not None:
            self.ffmpeg_path_label.configure(text_color=UIConfig.accent_color())

    def _apply_label_theme(self, widget: tk.Misc) -> None:
        try:
            children = widget.winfo_children()
        except tk.TclError:
            return
        for child in children:
            if isinstance(child, CTkLabel):
                child.configure(text_color=UIConfig.accent_color())
            self._apply_label_theme(child)

    def _apply_segmented_palette(self, *controls: SegmentedControl) -> None:
        palette = UIConfig.segmented_palette()
        for control in controls:
            control.apply_palette(palette)

    def _apply_settings_button_styles(self) -> None:
        if self.advanced_toggle_button is not None:
            self.advanced_toggle_button.configure(
                bg_color=UIConfig.window_color(),
                fg_color=UIConfig.bg_color(),
                hover_color=UIConfig.button_color(),
                text_color=UIConfig.accent_color(),
                border_color=UIConfig.accent_color(),
                border_width=2,
            )
        if self.refresh_button is not None:
            self.refresh_button.configure(
                bg_color=UIConfig.bg_color(),
                fg_color=UIConfig.button_color(),
                hover_color=UIConfig.hover_color(),
                text_color=UIConfig.button_text_color(),
                border_color=UIConfig.accent_color(),
                border_width=2,
            )
        if self.check_now_button is not None:
            self.check_now_button.configure(
                bg_color=UIConfig.bg_color(),
                fg_color=UIConfig.button_color(),
                hover_color=UIConfig.hover_color(),
                text_color=UIConfig.button_text_color(),
                border_color=UIConfig.accent_color(),
                border_width=2,
            )
        if self.reset_notices_button is not None:
            self.reset_notices_button.configure(
                bg_color=UIConfig.bg_color(),
                fg_color=UIConfig.bg_color(),
                hover_color=UIConfig.window_color(),
                text_color=UIConfig.accent_color(),
                border_color=UIConfig.accent_color(),
                border_width=2,
            )
        if self.ffmpeg_path_label is not None:
            self.ffmpeg_path_label.configure(
                fg_color="transparent",
                text_color=UIConfig.accent_color(),
            )
        for button in (self.ffmpeg_choose_button, self.ffmpeg_auto_button):
            if button is None:
                continue
            button.configure(
                bg_color=UIConfig.bg_color(),
                fg_color=UIConfig.button_color(),
                hover_color=UIConfig.hover_color(),
                text_color=UIConfig.button_text_color(),
                border_color=UIConfig.accent_color(),
                border_width=2,
            )
        for button in (self.cancel_button, self.save_button):
            if button is None:
                continue
            button.configure(
                bg_color=UIConfig.window_color(),
                fg_color=UIConfig.button_color(),
                hover_color=UIConfig.hover_color(),
                text_color=UIConfig.button_text_color(),
                border_color=UIConfig.accent_color(),
                border_width=2,
            )

    def _advanced_toggle_text(self) -> str:
        return "▼  Processing Options" if self.advanced_expanded else "▶  Processing Options"

    def _toggle_advanced_section(self) -> None:
        self.advanced_expanded = not self.advanced_expanded
        self._set_advanced_visibility()
        if self.window is not None and self.window.winfo_exists():
            self.window.after_idle(lambda: self._center_window(preserve_position=True))

    def _set_advanced_visibility(self) -> None:
        if self.advanced_toggle_button is not None:
            self.advanced_toggle_button.configure(text=self._advanced_toggle_text())

        if self.advanced_panel is None:
            return

        if self.advanced_expanded:
            self.advanced_panel.grid(row=2, column=0, sticky="we", padx=12, pady=(0, 8))
        else:
            self.advanced_panel.grid_remove()
