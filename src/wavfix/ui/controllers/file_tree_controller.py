"""File selection/inspection controller for the WavFix tree view."""

from __future__ import annotations

import os
import platform
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Literal, cast

from ...core import InputFileSpec, inspect_file, scan_input_specs
from ...core.constants import SUPPORTED_EXTENSIONS
from ...core.inspection import format_kind_label, inspect_wav_metadata, short_status
from ...core.models import (
    BitDepthPolicy,
    FileInspection,
    MetadataPolicy,
    MultiChannelPolicy,
    SampleRatePolicy,
    WavMetadata,
)
from ..theme import UIConfig
from ..windows.dialogs import show_warning

_AppKit: Any = None
if platform.system() == "Darwin":
    try:
        import AppKit as _AppKit
    except Exception:  # pragma: no cover - environment dependent
        _AppKit = None

NSApplication = getattr(_AppKit, "NSApplication", None)
NSModalResponseOK = getattr(_AppKit, "NSModalResponseOK", None)
NSOpenPanel = getattr(_AppKit, "NSOpenPanel", None)

_FileSignature = tuple[int, int]
_ProcessingOptions = tuple[str, str, str, str, str] | tuple[str, str, str, str, str, str, str]
_InspectionSignature = tuple[int, int, str, str, str, str, str]


class FileTreeController:
    """UI controller for selecting, inspecting, and displaying files."""

    def __init__(
        self,
        files_tree: ttk.Treeview,
        root: tk.Tk,
        on_tree_changed,
        on_loading_changed=None,
        get_processing_options=None,
    ) -> None:
        self.files_tree = files_tree
        self.root = root
        self.on_tree_changed = on_tree_changed
        self.on_loading_changed = on_loading_changed
        self.get_processing_options = get_processing_options
        self.input_specs: list[InputFileSpec] = []
        self._loading_selection = False
        self._reinspect_in_flight = False
        self._reinspect_pending = False
        self._pending_reinspect_options: _ProcessingOptions | None = None
        self._current_load_origin: Literal["picker", "dnd"] = "picker"
        self._inspection_cache: dict[Path, tuple[_InspectionSignature, FileInspection]] = {}
        self._wav_metadata_cache: dict[Path, tuple[_FileSignature, WavMetadata]] = {}
        self._cache_lock = threading.Lock()
        self._tree_update_token = 0

    def _file_types(self) -> tuple[str, str]:
        return (
            "Common Album Files",
            " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS),
        )

    def get_input_specs(self) -> list[InputFileSpec]:
        return list(self.input_specs)

    def is_loading(self) -> bool:
        return self._loading_selection

    def _current_processing_options(self) -> tuple[str, str, str, str, str]:
        profile = "preserve_supported_rate"
        multichannel_policy = "downmix"
        metadata_policy = "best_effort"
        sample_rate_policy = "convert_nearest"
        bit_depth_policy = "convert"
        if self.get_processing_options:
            options = self.get_processing_options()
            (
                profile,
                multichannel_policy,
                metadata_policy,
                sample_rate_policy,
                bit_depth_policy,
            ) = options[:5]
        return (
            profile,
            multichannel_policy,
            metadata_policy,
            sample_rate_policy,
            bit_depth_policy,
        )

    @staticmethod
    def _file_signature(path: Path) -> _FileSignature | None:
        try:
            stat = path.stat()
        except OSError:
            return None
        return stat.st_size, stat.st_mtime_ns

    @staticmethod
    def _inspection_signature(
        *,
        file_signature: _FileSignature,
        profile: str,
        multichannel_policy: str,
        metadata_policy: str,
        sample_rate_policy: str,
        bit_depth_policy: str,
    ) -> _InspectionSignature:
        return (
            file_signature[0],
            file_signature[1],
            profile,
            multichannel_policy,
            metadata_policy,
            sample_rate_policy,
            bit_depth_policy,
        )

    @staticmethod
    def _inspection_workers(total: int) -> int:
        if total <= 1:
            return 1
        cpu_count = max(1, os.cpu_count() or 4)
        return max(2, min(8, cpu_count, total))

    def request_root_focus(self) -> None:
        """Request app focus using a gentle, async UI-thread call."""

        def _focus() -> None:
            try:
                self.root.lift()
                self.root.focus_set()
            except tk.TclError:
                return

        self.root.after(0, _focus)

    def request_root_focus_force(self) -> None:
        """Request app focus using a stronger force-focus path."""

        def _focus() -> None:
            try:
                self.root.lift()
                if platform.system() == "Darwin":
                    self.root.focus_force()
                else:
                    self.root.focus_set()
            except tk.TclError:
                return

        self.root.after(0, _focus)

    def _choose_files_and_folders(self) -> list[str]:
        """Open a single native picker for files and folders."""
        if platform.system() == "Darwin":
            if NSOpenPanel is not None and NSModalResponseOK is not None:
                try:
                    if NSApplication is not None:
                        app = NSApplication.sharedApplication()
                        app.activateIgnoringOtherApps_(True)
                    panel = NSOpenPanel.openPanel()
                    panel.setCanChooseFiles_(True)
                    panel.setCanChooseDirectories_(True)
                    panel.setAllowsMultipleSelection_(True)
                    panel.setCanCreateDirectories_(False)
                    panel.setPrompt_("Open")
                    panel.setMessage_("Select files and/or folders")
                    response = panel.runModal()
                    if response == NSModalResponseOK:
                        return [str(url.path()) for url in panel.URLs()]
                    return []
                except Exception as exc:  # pragma: no cover - platform/runtime dependent
                    show_warning(
                        self.root,
                        title="Native Picker Error",
                        message=(
                            "The native mixed file/folder picker could not open.\n"
                            "WavFix will fall back to the standard file picker.\n\n"
                            f"Details: {exc}"
                        ),
                    )
            else:
                show_warning(
                    self.root,
                    title="Native Picker Unavailable",
                    message=(
                        "Native mixed file/folder picker is unavailable in this environment.\n"
                        "WavFix will use the standard file picker."
                    ),
                )

        selected_files = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[self._file_types()],
        )
        return [str(path) for path in selected_files]

    def select_inputs(self) -> None:
        selected_items = self._choose_files_and_folders()
        self.request_root_focus()
        if not selected_items:
            return

        self.load_selected_items(selected_items, origin="picker")

    def load_selected_items(
        self,
        selected_items: list[str],
        *,
        origin: Literal["picker", "dnd"] = "picker",
    ) -> None:
        if not selected_items or self._loading_selection:
            return

        self._current_load_origin = origin
        self._loading_selection = True
        if self.on_loading_changed:
            self.on_loading_changed(True)
        self.root.configure(cursor="watch")
        worker = threading.Thread(
            target=self._load_selected_items_worker,
            args=(selected_items,),
            daemon=True,
        )
        worker.start()

    def get_inspections_for_specs(
        self,
        input_specs: list[InputFileSpec],
        *,
        profile: str,
        multichannel_policy: str,
        metadata_policy: str,
        sample_rate_policy: str,
        bit_depth_policy: str,
    ) -> list[FileInspection]:
        return self._inspect_specs(
            input_specs,
            profile=profile,
            multichannel_policy=multichannel_policy,
            metadata_policy=metadata_policy,
            sample_rate_policy=sample_rate_policy,
            bit_depth_policy=bit_depth_policy,
            parallel=True,
        )

    def _inspect_specs(
        self,
        input_specs: list[InputFileSpec],
        *,
        profile: str,
        multichannel_policy: str,
        metadata_policy: str,
        sample_rate_policy: str,
        bit_depth_policy: str,
        parallel: bool,
    ) -> list[FileInspection]:
        if not input_specs:
            return []

        if not parallel or len(input_specs) <= 1:
            return self._inspect_specs_serial(
                input_specs,
                profile=profile,
                multichannel_policy=multichannel_policy,
                metadata_policy=metadata_policy,
                sample_rate_policy=sample_rate_policy,
                bit_depth_policy=bit_depth_policy,
            )

        return self._inspect_specs_parallel(
            input_specs,
            profile=profile,
            multichannel_policy=multichannel_policy,
            metadata_policy=metadata_policy,
            sample_rate_policy=sample_rate_policy,
            bit_depth_policy=bit_depth_policy,
        )

    def _inspect_specs_parallel(
        self,
        input_specs: list[InputFileSpec],
        *,
        profile: str,
        multichannel_policy: str,
        metadata_policy: str,
        sample_rate_policy: str,
        bit_depth_policy: str,
    ) -> list[FileInspection]:
        results: list[FileInspection | None] = [None] * len(input_specs)
        max_workers = self._inspection_workers(len(input_specs))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    self._inspect_spec,
                    spec,
                    profile=profile,
                    multichannel_policy=multichannel_policy,
                    metadata_policy=metadata_policy,
                    sample_rate_policy=sample_rate_policy,
                    bit_depth_policy=bit_depth_policy,
                ): index
                for index, spec in enumerate(input_specs)
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                results[index] = future.result()

        return [cast(FileInspection, inspection) for inspection in results]

    def _inspect_specs_serial(
        self,
        input_specs: list[InputFileSpec],
        *,
        profile: str,
        multichannel_policy: str,
        metadata_policy: str,
        sample_rate_policy: str,
        bit_depth_policy: str,
    ) -> list[FileInspection]:
        return [
            self._inspect_spec(
                spec,
                profile=profile,
                multichannel_policy=multichannel_policy,
                metadata_policy=metadata_policy,
                sample_rate_policy=sample_rate_policy,
                bit_depth_policy=bit_depth_policy,
            )
            for spec in input_specs
        ]

    def _load_selected_items_worker(self, selected_items: list[str]) -> None:
        try:
            input_specs = scan_input_specs(selected_items)
            (
                profile,
                multichannel_policy,
                metadata_policy,
                sample_rate_policy,
                bit_depth_policy,
            ) = self._current_processing_options()
            inspections = self._inspect_specs(
                input_specs,
                profile=profile,
                multichannel_policy=multichannel_policy,
                metadata_policy=metadata_policy,
                sample_rate_policy=sample_rate_policy,
                bit_depth_policy=bit_depth_policy,
                parallel=True,
            )
        except Exception as exc:  # pragma: no cover - UI runtime protection
            self.root.after(0, self._handle_loading_error, str(exc))
            return

        self.root.after(0, self._apply_loaded_selection, input_specs, inspections)

    def _finish_loading(self) -> None:
        self._loading_selection = False
        self._current_load_origin = "picker"
        self.root.configure(cursor="")
        if self.on_loading_changed:
            self.on_loading_changed(False)

    def _handle_loading_error(self, error_message: str) -> None:
        self._finish_loading()
        messagebox.showerror("Failed to load selection", error_message)

    def _apply_loaded_selection(
        self,
        input_specs: list[InputFileSpec],
        inspections: list[FileInspection],
    ) -> None:
        load_origin = self._current_load_origin
        self._finish_loading()

        if not input_specs:
            return

        self.add_files_to_tree(input_specs, inspections)
        if load_origin == "dnd":
            self.request_root_focus_force()
        else:
            self.request_root_focus()

    def add_files_to_tree(
        self,
        input_specs: list[InputFileSpec],
        inspections: list[FileInspection] | None = None,
    ) -> None:
        self._tree_update_token += 1
        token = self._tree_update_token

        if inspections is None:
            (
                profile,
                multichannel_policy,
                metadata_policy,
                sample_rate_policy,
                bit_depth_policy,
            ) = self._current_processing_options()
            inspections = self._inspect_specs(
                input_specs,
                profile=profile,
                multichannel_policy=multichannel_policy,
                metadata_policy=metadata_policy,
                sample_rate_policy=sample_rate_policy,
                bit_depth_policy=bit_depth_policy,
                parallel=True,
            )

        if self._update_existing_rows_in_place(input_specs, inspections):
            self.input_specs = list(input_specs)
            self.on_tree_changed()
            return

        self.input_specs = list(input_specs)
        self.files_tree.delete(*self.files_tree.get_children())

        rows: list[tuple[tuple[str, str, str, str, str], str]] = []
        for input_spec, inspection in zip(input_specs, inspections, strict=True):
            color_tag = inspection.color_tag
            format_str = format_kind_label(inspection.format_kind)
            status_str = short_status(inspection)
            rows.append(
                (
                    (
                        input_spec.path.name,
                        format_str,
                        status_str,
                        str(input_spec.path),
                        inspection.reason,
                    ),
                    color_tag,
                )
            )

        for tag in {tag for _, tag in rows}:
            self.files_tree.tag_configure(tag, foreground=self._color_for_tag(tag))

        if len(rows) <= 250:
            for values, color_tag in rows:
                self.files_tree.insert("", "end", values=values, tags=(color_tag,))
            if self.files_tree.get_children():
                self.files_tree.see(self.files_tree.get_children()[-1])
            self.on_tree_changed()
            return

        self._insert_rows_batched(rows, token=token)

    def _update_existing_rows_in_place(
        self,
        input_specs: list[InputFileSpec],
        inspections: list[FileInspection],
    ) -> bool:
        children = self.files_tree.get_children()
        if len(children) != len(input_specs):
            return False

        path_to_item: dict[str, str] = {}
        for item in children:
            values = cast(tuple[str, ...], self.files_tree.item(item, "values"))
            if len(values) < 4:
                return False
            path_to_item[values[3]] = item

        if len(path_to_item) != len(children):
            return False

        expected_paths = {str(spec.path) for spec in input_specs}
        if set(path_to_item.keys()) != expected_paths:
            return False

        tag_colors = {
            inspection.color_tag: self._color_for_tag(inspection.color_tag)
            for inspection in inspections
        }
        for tag, color in tag_colors.items():
            self.files_tree.tag_configure(tag, foreground=color)

        for row_index, (input_spec, inspection) in enumerate(
            zip(input_specs, inspections, strict=True)
        ):
            item = path_to_item[str(input_spec.path)]
            format_str = format_kind_label(inspection.format_kind)
            status_str = short_status(inspection)
            color_tag = inspection.color_tag
            new_values = (
                input_spec.path.name,
                format_str,
                status_str,
                str(input_spec.path),
                inspection.reason,
            )
            new_tags = (color_tag,)
            current_values = cast(tuple[str, ...], self.files_tree.item(item, "values"))
            current_tags = tuple(cast(tuple[str, ...], self.files_tree.item(item, "tags")))
            if current_values != new_values or current_tags != new_tags:
                self.files_tree.item(
                    item,
                    values=new_values,
                    tags=new_tags,
                )
            if children[row_index] != item:
                self.files_tree.move(item, "", row_index)

        return True

    def _insert_rows_batched(
        self,
        rows: list[tuple[tuple[str, str, str, str, str], str]],
        token: int,
        start: int = 0,
    ) -> None:
        if token != self._tree_update_token:
            return

        batch_size = 200
        end = min(start + batch_size, len(rows))
        for values, color_tag in rows[start:end]:
            self.files_tree.insert("", "end", values=values, tags=(color_tag,))

        if end < len(rows):
            self.root.after_idle(self._insert_rows_batched, rows, token, end)
            return

        if self.files_tree.get_children():
            self.files_tree.see(self.files_tree.get_children()[-1])
        self.on_tree_changed()

    def clear_selection(self) -> None:
        self.input_specs = []
        self._tree_update_token += 1
        with self._cache_lock:
            self._inspection_cache.clear()
            self._wav_metadata_cache.clear()

    def reinspect_current_selection(self) -> None:
        self.reinspect_current_selection_async()

    def reinspect_current_selection_async(
        self,
        options: _ProcessingOptions | None = None,
    ) -> None:
        if not self.input_specs or self._loading_selection or self._reinspect_in_flight:
            if self._reinspect_in_flight:
                self._reinspect_pending = True
                if options is not None:
                    self._pending_reinspect_options = options
            return
        self._reinspect_in_flight = True
        specs_snapshot = list(self.input_specs)
        resolved_options = options or self._current_processing_options()
        worker = threading.Thread(
            target=self._reinspect_worker,
            args=(specs_snapshot, resolved_options),
            daemon=True,
        )
        worker.start()

    def _reinspect_worker(
        self,
        specs_snapshot: list[InputFileSpec],
        options: _ProcessingOptions,
    ) -> None:
        try:
            (
                profile,
                multichannel_policy,
                metadata_policy,
                sample_rate_policy,
                bit_depth_policy,
            ) = options[:5]
            inspections = self._inspect_specs(
                specs_snapshot,
                profile=profile,
                multichannel_policy=multichannel_policy,
                metadata_policy=metadata_policy,
                sample_rate_policy=sample_rate_policy,
                bit_depth_policy=bit_depth_policy,
                parallel=True,
            )
        except Exception as exc:  # pragma: no cover - UI runtime protection
            self.root.after(0, self._finish_reinspect_error, str(exc))
            return
        self.root.after(0, self._apply_reinspection, specs_snapshot, inspections)

    def _finish_reinspect_error(self, error_message: str) -> None:
        self._reinspect_in_flight = False
        should_retry = self._reinspect_pending
        retry_options = self._pending_reinspect_options
        self._reinspect_pending = False
        self._pending_reinspect_options = None
        if should_retry:
            self.reinspect_current_selection_async(retry_options)
        messagebox.showerror("Failed to refresh selection", error_message)

    def _apply_reinspection(
        self,
        specs_snapshot: list[InputFileSpec],
        inspections: list[FileInspection],
    ) -> None:
        self._reinspect_in_flight = False
        should_retry = self._reinspect_pending
        retry_options = self._pending_reinspect_options
        self._reinspect_pending = False
        self._pending_reinspect_options = None
        current_paths = [spec.path for spec in self.input_specs]
        snapshot_paths = [spec.path for spec in specs_snapshot]
        if current_paths != snapshot_paths:
            if should_retry:
                self.reinspect_current_selection_async(retry_options)
            return
        self.add_files_to_tree(specs_snapshot, inspections)
        if should_retry:
            self.reinspect_current_selection_async(retry_options)

    def refresh_tree_colors(self) -> None:
        tags: set[str] = set()
        for item in self.files_tree.get_children():
            item_tags = cast(tuple[str, ...], self.files_tree.item(item, "tags"))
            if item_tags:
                tags.add(item_tags[0])
        for color_tag in tags:
            self.files_tree.tag_configure(color_tag, foreground=self._color_for_tag(color_tag))

    @staticmethod
    def _color_for_tag(tag: str) -> str:
        if tag == "neutral":
            return UIConfig.neutral_files_color()
        if tag == "green":
            return UIConfig.green_files_color()
        if tag == "yellow":
            return UIConfig.yellow_files_color()
        if tag == "orange":
            return UIConfig.orange_files_color()
        if tag == "red":
            return UIConfig.red_files_color()
        return UIConfig.blue_files_color()

    def _inspect_spec(
        self,
        spec: InputFileSpec,
        *,
        profile: str,
        multichannel_policy: str,
        metadata_policy: str,
        sample_rate_policy: str,
        bit_depth_policy: str,
    ) -> FileInspection:
        file_signature = self._file_signature(spec.path)
        inspection_signature: _InspectionSignature | None = None
        if file_signature is not None:
            inspection_signature = self._inspection_signature(
                file_signature=file_signature,
                profile=profile,
                multichannel_policy=multichannel_policy,
                metadata_policy=metadata_policy,
                sample_rate_policy=sample_rate_policy,
                bit_depth_policy=bit_depth_policy,
            )

        with self._cache_lock:
            cached_entry = self._inspection_cache.get(spec.path)
            metadata_entry = self._wav_metadata_cache.get(spec.path)

        if cached_entry is not None and inspection_signature is not None:
            cached_signature, cached_inspection = cached_entry
            if cached_signature == inspection_signature:
                return cached_inspection

        if (
            metadata_entry is not None
            and file_signature is not None
            and metadata_entry[0] == file_signature
            and (metadata_policy != "strict_preserve" or bool(metadata_entry[1].chunks))
        ):
            inspection = inspect_wav_metadata(
                spec.path,
                cast(WavMetadata, metadata_entry[1]),
                profile_name=profile,
                allow_conversion=True,
                multichannel_policy=cast(MultiChannelPolicy, multichannel_policy),
                metadata_policy=cast(MetadataPolicy, metadata_policy),
                sample_rate_policy=cast(SampleRatePolicy, sample_rate_policy),
                bit_depth_policy=cast(BitDepthPolicy, bit_depth_policy),
            )
        else:
            inspection = inspect_file(
                spec.path,
                profile_name=profile,
                allow_conversion=True,
                multichannel_policy=cast(MultiChannelPolicy, multichannel_policy),
                metadata_policy=cast(MetadataPolicy, metadata_policy),
                sample_rate_policy=cast(SampleRatePolicy, sample_rate_policy),
                bit_depth_policy=cast(BitDepthPolicy, bit_depth_policy),
            )

        with self._cache_lock:
            if inspection_signature is not None:
                self._inspection_cache[spec.path] = (inspection_signature, inspection)
            if inspection.wav_metadata is not None and file_signature is not None:
                self._wav_metadata_cache[spec.path] = (file_signature, inspection.wav_metadata)

        return inspection
