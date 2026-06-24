"""Export/processing controller for the WavFix UI."""

from __future__ import annotations

import os
import queue as queue_module
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, cast

from customtkinter import CTkTextbox

from ...core import InputFileSpec, ProcessRequest, process_request
from ...core.models import (
    BitDepthPolicy,
    ConverterBackend,
    MetadataPolicy,
    MultiChannelPolicy,
    OverwritePolicy,
    ProfileName,
    RepairAction,
    SampleRatePolicy,
)
from ..theme import UIConfig
from ..windows.dialogs import ask_warning_yes_no, show_ffmpeg_recommendation, show_warning
from .file_tree_controller import FileTreeController


class ExportController:
    """Coordinates UI export actions with the core processing pipeline."""

    def __init__(
        self,
        root: tk.Tk,
        output_text: CTkTextbox,
        file_controller: FileTreeController,
        on_processing_changed=None,
        get_processing_options=None,
    ) -> None:
        self.root = root
        self.output_text = output_text
        self.file_controller = file_controller
        self.on_processing_changed = on_processing_changed
        self.get_processing_options = get_processing_options
        self.queue: queue_module.Queue[tuple[str, str]] = queue_module.Queue()
        self.processing_done = threading.Event()
        self._processing = False
        self.refresh_output_tags()

    def is_processing(self) -> bool:
        return self._processing

    def _set_processing(self, processing: bool) -> None:
        self._processing = processing
        if self.on_processing_changed:
            self.on_processing_changed(processing)

    def initiate_export(self) -> None:
        if self._processing:
            return

        input_specs = self.file_controller.get_input_specs()
        if not input_specs:
            return

        profile = "preserve_supported_rate"
        multichannel_policy = "downmix"
        metadata_policy = "best_effort"
        sample_rate_policy = "convert_nearest"
        bit_depth_policy = "convert"
        converter_backend = "builtin"
        ffmpeg_path = ""
        if self.get_processing_options:
            (
                profile,
                multichannel_policy,
                metadata_policy,
                sample_rate_policy,
                bit_depth_policy,
                converter_backend,
                ffmpeg_path,
            ) = self.get_processing_options()

        allow_conversion = self._prompt_for_conversion_if_needed(
            input_specs=input_specs,
            profile=profile,
            multichannel_policy=multichannel_policy,
            metadata_policy=metadata_policy,
            sample_rate_policy=sample_rate_policy,
            bit_depth_policy=bit_depth_policy,
        )
        if allow_conversion is None:
            return
        resolved_ffmpeg_path = ""
        if allow_conversion and converter_backend == "ffmpeg":
            resolved_ffmpeg_path = self._resolve_ffmpeg_executable(ffmpeg_path)
            if not resolved_ffmpeg_path:
                self._show_ffmpeg_recommendation_if_needed()
                return

        output_directory = filedialog.askdirectory(title="Select Output Directory")
        if not output_directory:
            return

        overwrite_policy = self._resolve_overwrite_policy(Path(output_directory), input_specs)

        request = ProcessRequest(
            output_dir=Path(output_directory),
            overwrite_policy=overwrite_policy,
            input_paths=[spec.path for spec in input_specs],
            batch_mode=False,
            input_specs=input_specs,
            profile=cast(ProfileName, profile),
            performance_mode=UIConfig.PERFORMANCE_MODE,
            allow_conversion=allow_conversion,
            multichannel_policy=cast(MultiChannelPolicy, multichannel_policy),
            metadata_policy=cast(MetadataPolicy, metadata_policy),
            sample_rate_policy=cast(SampleRatePolicy, sample_rate_policy),
            bit_depth_policy=cast(BitDepthPolicy, bit_depth_policy),
            converter_backend=cast(ConverterBackend, converter_backend),
            ffmpeg_path=resolved_ffmpeg_path,
        )

        self._set_processing(True)
        self.processing_done.clear()
        self._drain_output_queue()
        self._update_output_window()

        processing_thread = threading.Thread(
            target=self._process_selected_files,
            args=(request,),
            daemon=True,
        )
        processing_thread.start()

    def _resolve_overwrite_policy(
        self,
        output_directory: Path,
        input_specs: list[InputFileSpec],
    ) -> OverwritePolicy:
        existing_items = set(os.listdir(output_directory)) if output_directory.exists() else set()

        has_conflict = any(
            (spec.source_root.name if spec.source_root is not None else spec.path.name)
            in existing_items
            for spec in input_specs
        )

        if has_conflict:
            should_overwrite = messagebox.askyesno(
                title="Overwrite existing items?",
                message="Do you want to overwrite existing files or folders?",
            )
            return "yes" if should_overwrite else "no"

        return "yes"

    def _process_selected_files(self, request: ProcessRequest) -> None:
        processed_outputs: list[Path] = []
        try:
            result = process_request(
                request,
                progress_callback=self._on_progress,
            )
            processed_outputs = list(result.outputs)
            success_count = result.unchanged + result.header_fixed + result.converted
            rejected_count = result.rejected
            error_count = len(result.errors)
            has_failures = rejected_count > 0 or error_count > 0
            if has_failures and success_count == 0:
                header_style = "summary_error"
            elif has_failures:
                header_style = "summary_warning"
            else:
                header_style = "summary"

            self._enqueue_output("\n\nSummary:", header_style)
            self._enqueue_output(f"\n  Unchanged: {result.unchanged}", "summary")
            self._enqueue_output(f"\n  Header-fixed: {result.header_fixed}", "summary")
            self._enqueue_output(f"\n  Converted: {result.converted}", "summary")
            self._enqueue_output(
                f"\n  Rejected: {rejected_count}",
                "error" if rejected_count > 0 else "summary",
            )
            self._enqueue_output(
                f"\n  Errors: {error_count}",
                "error" if error_count > 0 else "summary",
            )
            if result.warnings:
                self._enqueue_output("\nWarnings:", "warning")
                for warning in result.warnings:
                    self._enqueue_output(
                        f"\n  - {self._format_warning_text(warning)}",
                        "warning",
                    )
            for error in result.errors:
                self._enqueue_output(f"\nERROR: {error}", "error")
        except Exception as exc:  # pragma: no cover - UI runtime protection
            self._enqueue_output(f"\n\nError while processing files: {exc}", "error")
        finally:
            self.processing_done.set()
            self.root.after(0, self._set_processing, False)
            if processed_outputs:
                self.root.after(50, self._show_output_files_in_tree, processed_outputs)

    def _on_progress(self, event: Any) -> None:
        if event.kind == "done":
            self._enqueue_output("\n\nDone!", "summary")
            return
        message = str(event.message)
        if event.kind == "warning":
            message = self._format_warning_text(message)
        self._enqueue_output(f"\n{message}", self._style_for_progress_event(event))

    def _prompt_for_conversion_if_needed(
        self,
        *,
        input_specs: list[InputFileSpec],
        profile: str,
        multichannel_policy: str,
        metadata_policy: str,
        sample_rate_policy: str,
        bit_depth_policy: str,
    ) -> bool | None:
        inspections = self.file_controller.get_inspections_for_specs(
            input_specs,
            profile=profile,
            multichannel_policy=multichannel_policy,
            metadata_policy=metadata_policy,
            sample_rate_policy=sample_rate_policy,
            bit_depth_policy=bit_depth_policy,
        )
        conversion_required = [item for item in inspections if item.action == RepairAction.CONVERT]
        if not conversion_required:
            return False
        if UIConfig.CONVERSION_WARNING_CHOICE == "allow":
            return True
        if UIConfig.CONVERSION_WARNING_CHOICE == "reject":
            return False

        reasons = sorted({item.reason for item in conversion_required})
        reason_preview = "\n".join(f"- {reason}" for reason in reasons[:4])
        if len(reasons) > 4:
            reason_preview += "\n- (additional reasons omitted)"

        should_convert, do_not_show_again = cast(
            tuple[bool, bool],
            ask_warning_yes_no(
                self.root,
                title="Audio Conversion Required",
                message=(
                    f"{len(conversion_required)} file(s) require audio-data conversion.\n\n"
                    "Yes = convert those files to Pioneer-compatible PCM.\n"
                    "No = continue but reject conversion-required files.\n\n"
                    f"Reasons:\n{reason_preview}"
                ),
                show_do_not_show_again=True,
            ),
        )
        if do_not_show_again:
            UIConfig.CONVERSION_WARNING_CHOICE = "allow" if should_convert else "reject"
            UIConfig.save()
        return should_convert

    @staticmethod
    def _resolve_ffmpeg_executable(ffmpeg_path: str) -> str:
        if ffmpeg_path.strip():
            candidate = Path(ffmpeg_path).expanduser()
            if candidate.is_file():
                return str(candidate)
            return ""
        return shutil.which("ffmpeg") or ""

    def _show_ffmpeg_recommendation_if_needed(self) -> None:
        if not UIConfig.SHOW_FFMPEG_RECOMMENDATION:
            show_warning(
                self.root,
                title="FFmpeg Not Found",
                message=(
                    "FFmpeg conversion is enabled, but WavFix could not find FFmpeg.\n\n"
                    "Choose an FFmpeg executable in Settings, switch Converter back to "
                    "Built-in, or install FFmpeg and use PATH auto-detection."
                ),
            )
            return

        def _disable_recommendation() -> None:
            UIConfig.SHOW_FFMPEG_RECOMMENDATION = False
            UIConfig.save()

        show_ffmpeg_recommendation(
            self.root,
            on_do_not_show_again=_disable_recommendation,
        )

    def _drain_output_queue(self) -> None:
        while True:
            try:
                self.queue.get_nowait()
            except queue_module.Empty:
                break

    def _update_output_window(self) -> None:
        messages: list[tuple[str, str]] = []
        while True:
            try:
                messages.append(self.queue.get_nowait())
            except queue_module.Empty:
                break

        if messages:
            self.output_text.configure(state="normal")
            for style, message in messages:
                self.output_text.insert(tk.END, message, f"out_{style}")
            self.output_text.see(tk.END)
            self.output_text.configure(state="disabled")

        if not self.processing_done.is_set() or not self.queue.empty():
            self.root.after(100, self._update_output_window)

    def refresh_output_tags(self) -> None:
        self.output_text.tag_config("out_default", foreground=UIConfig.output_text_color())
        self.output_text.tag_config("out_summary", foreground=UIConfig.green_files_color())
        self.output_text.tag_config("out_summary_warning", foreground=UIConfig.orange_files_color())
        self.output_text.tag_config("out_summary_error", foreground=UIConfig.red_files_color())
        self.output_text.tag_config("out_neutral", foreground=UIConfig.neutral_files_color())
        self.output_text.tag_config("out_pass", foreground=UIConfig.green_files_color())
        self.output_text.tag_config("out_header", foreground=UIConfig.green_files_color())
        self.output_text.tag_config("out_convert", foreground=UIConfig.green_files_color())
        self.output_text.tag_config("out_warning", foreground=UIConfig.red_files_color())
        self.output_text.tag_config("out_reject", foreground=UIConfig.red_files_color())
        self.output_text.tag_config("out_error", foreground=UIConfig.red_files_color())

    def _enqueue_output(self, message: str, style: str = "default") -> None:
        self.queue.put((style, message))

    @staticmethod
    def _style_for_progress_event(event: Any) -> str:
        if event.kind == "error":
            return "error"
        if event.kind == "warning":
            return "warning"
        if event.kind == "reject":
            return "reject"
        message = str(event.message).lower()
        if message.startswith("unchanged copy:"):
            try:
                output_path = Path(str(event.message).split(":", 1)[1].strip())
            except Exception:
                return "pass"
            return "pass" if output_path.suffix.lower() == ".wav" else "neutral"
        if message.startswith("header fixed:"):
            return "header"
        if message.startswith("converted:"):
            return "convert"
        return "default"

    def _show_output_files_in_tree(self, output_paths: list[Path]) -> None:
        selected_items = [str(path) for path in output_paths if path.exists()]
        if not selected_items:
            return
        self.file_controller.load_selected_items(selected_items)

    @staticmethod
    def _format_warning_text(message: str) -> str:
        """Render warning lines with filename-only paths for cleaner UI output."""
        warning_prefix = ""
        raw = message.strip()
        lowered = raw.lower()
        if lowered.startswith("warning:"):
            warning_prefix = "Warning: "
            raw = raw.split(":", 1)[1].strip()

        separator = ": "
        if separator not in raw:
            return f"{warning_prefix}{raw}"

        file_part, details = raw.split(separator, 1)
        file_part = file_part.strip()
        details = details.strip()
        if not file_part:
            return f"{warning_prefix}{raw}"

        filename = Path(file_part).name
        if not filename:
            return f"{warning_prefix}{raw}"
        return f"{warning_prefix}{filename}: {details}"
