"""Main WavFix UI shell orchestration."""

from __future__ import annotations

import platform
import sys
import threading
import time
import tkinter as tk
from math import ceil
from pathlib import Path
from tkinter import ttk

from customtkinter import CTkButton, CTkFrame, CTkTextbox
from tkinterdnd2 import DND_FILES, TkinterDnD

from ..core.processing import warm_conversion_backend
from ..core.update_checker import fetch_latest_release, is_newer_version
from .behaviors.dnd import DnDHandler
from .behaviors.tooltip import ToolTip
from .behaviors.treeview_style import configure_treeview_style, create_treeview_style
from .controllers.export_controller import ExportController
from .controllers.file_tree_controller import FileTreeController
from .theme import UIConfig
from .windows.dialogs import show_info, show_update_available, show_warning
from .windows.settings_window import SettingsWindow

_UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


class WavFixApp:
    """Main UI application class."""

    def __init__(self) -> None:
        UIConfig.load()

        self.root = TkinterDnD.Tk()
        if platform.system() == "Darwin":
            self.root.withdraw()
        self.root.title("WavFix")
        self.root.resizable(False, False)

        self._edge_spacing = 20
        self.frame = tk.Frame(self.root, bg=UIConfig.bg_color(), padx=self._edge_spacing, pady=0)
        self.frame.grid()
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        self._settings_button_width = 86

        self.action_buttons_row: CTkFrame | None = None

        self._logo_row_height = 60
        self._resource_bases = self._build_resource_search_paths()
        self._version_file = self._resolve_resource_path("version.txt")
        self._version_text = self._read_version_text()
        self._logos_dir = self._resolve_resource_path("res/logos")
        self._logo_source_cache: dict[str, tk.PhotoImage] = {}
        self._logo_scaled_cache: dict[tuple[str, int], tk.PhotoImage] = {}
        self._left_logo_image: tk.PhotoImage | None = None
        self._right_logo_image: tk.PhotoImage | None = None

        self.tree_style = create_treeview_style()
        self._build_branding_row()
        self._build_input_panel()
        self._build_output_panel()
        self.files_tree = self._build_files_tree()
        self.treeview_tooltip = ToolTip(self.files_tree, "")

        self.file_controller = FileTreeController(
            self.files_tree,
            self.root,
            self._update_remove_tags_button,
            self._on_loading_changed,
            self._current_processing_options,
        )

        self.output_text = self._build_output_text()
        self.export_controller = ExportController(
            root=self.root,
            output_text=self.output_text,
            file_controller=self.file_controller,
            on_processing_changed=self._on_processing_changed,
            get_processing_options=self._current_processing_options,
        )

        self.settings_controller = SettingsWindow(
            self.root,
            on_theme_preview=self._update_widget_colors,
            on_refresh_status=self._refresh_status,
            on_check_updates=self._check_for_updates_manual,
        )

        self.select_files_button = self._build_select_files_button()
        self.settings_button = self._build_settings_button()
        self.remove_tags_button = self._build_remove_tags_button()
        self.frame.grid_rowconfigure(6, minsize=self._edge_spacing)

        dnd_handler = DnDHandler(self.file_controller, self.root)
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", dnd_handler)

        self.files_tree.bind("<Double-Button-1>", self._clear_treeview)
        self.output_text.bind("<Double-Button-1>", self._clear_output_text)
        self.root.bind("<Button-1>", self._clear_tree_selection_outside_input, add="+")

        self._quit_bindings()

        self._update_widget_colors()
        self._update_remove_tags_button()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if platform.system() == "Darwin":
            self.root.update_idletasks()
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        self.root.after(250, self._warm_conversion_backend)
        self.root.after(1500, self._check_for_updates_on_launch)

    def _build_branding_row(self) -> None:
        self.branding_frame = tk.Frame(
            master=self.frame,
            bg=UIConfig.bg_color(),
            height=self._logo_row_height,
        )
        self.branding_frame.grid(row=2, column=0, columnspan=2, sticky="we", pady=0)
        self.branding_frame.grid_columnconfigure(0, weight=0)
        self.branding_frame.grid_columnconfigure(1, weight=1)
        self.branding_frame.grid_columnconfigure(2, weight=0)
        self.branding_frame.grid_rowconfigure(0, minsize=self._logo_row_height, weight=1)
        self.branding_frame.grid_propagate(False)

        self.left_logo_label = tk.Label(
            master=self.branding_frame,
            bg=UIConfig.bg_color(),
            bd=0,
            highlightthickness=0,
            anchor="w",
        )
        self.left_logo_label.grid(row=0, column=0, sticky="nsw", padx=(8, 6), pady=0)

        self.right_cluster_frame = tk.Frame(
            master=self.branding_frame,
            bg=UIConfig.bg_color(),
            bd=0,
            highlightthickness=0,
        )
        self.right_cluster_frame.grid(row=0, column=2, sticky="nse", padx=(8, 8), pady=0)

        self.right_info_frame = tk.Frame(
            master=self.right_cluster_frame,
            bg=UIConfig.bg_color(),
            bd=0,
            highlightthickness=0,
        )
        self.right_info_frame.pack(side="right", anchor="e")

        self.version_label = tk.Label(
            master=self.right_info_frame,
            bg=UIConfig.bg_color(),
            bd=0,
            highlightthickness=0,
            anchor="w",
            text=self._version_text,
            fg=UIConfig.accent_color(),
            font=("Roboto", 10, "bold"),
        )
        self.version_label.pack(anchor="w", pady=(10, 0))

        self.author_label = tk.Label(
            master=self.right_info_frame,
            text="By Auragami",
            font=("Roboto", 10, "bold"),
            anchor="center",
            bg=UIConfig.bg_color(),
            fg=UIConfig.accent_color(),
            bd=0,
            highlightthickness=0,
        )
        self.author_label.pack(side="bottom", fill="x", pady=(0, 8))

        self.right_logo_label = tk.Label(
            master=self.right_cluster_frame,
            bg=UIConfig.bg_color(),
            bd=0,
            highlightthickness=0,
            anchor="w",
        )
        self.right_logo_label.pack(side="left", anchor="w", padx=(0, 6))

    def _build_input_panel(self) -> None:
        self.input_frame = CTkFrame(
            master=self.frame,
            fg_color=UIConfig.window_color(),
            border_color=UIConfig.accent_color(),
            border_width=1,
            corner_radius=10,
        )
        self.input_frame.grid(row=3, column=0, columnspan=2, sticky="we", pady=(0, 8))
        self.input_frame.grid_columnconfigure(0, weight=1)

    def _build_output_panel(self) -> None:
        self.output_frame = CTkFrame(
            master=self.frame,
            fg_color=UIConfig.window_color(),
            border_color=UIConfig.accent_color(),
            border_width=1,
            corner_radius=10,
        )
        self.output_frame.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="we",
            pady=(0, self._edge_spacing),
        )
        self.output_frame.grid_columnconfigure(0, weight=1)

    def _refresh_status(
        self,
        options: tuple[str, str, str, str, str, str, str] | None = None,
    ) -> None:
        if self.file_controller.is_loading() or self.export_controller.is_processing():
            return
        self.file_controller.reinspect_current_selection_async(options)

    def _current_processing_options(self) -> tuple[str, str, str, str, str, str, str]:
        return (
            UIConfig.PROFILE,
            UIConfig.MULTICHANNEL_POLICY,
            UIConfig.METADATA_POLICY,
            UIConfig.SAMPLE_RATE_POLICY,
            UIConfig.BIT_DEPTH_POLICY,
            UIConfig.CONVERTER_BACKEND,
            UIConfig.FFMPEG_PATH,
        )

    def _open_settings_panel(self) -> None:
        self.settings_controller.open()

    def _current_version(self) -> str:
        for line in self._version_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("version:"):
                return stripped.split(":", 1)[1].strip()
        return "0.0.0"

    def _check_for_updates_on_launch(self) -> None:
        if not UIConfig.CHECK_FOR_UPDATES:
            return
        now = int(time.time())
        if now - UIConfig.LAST_UPDATE_CHECK < _UPDATE_CHECK_INTERVAL_SECONDS:
            return
        self._check_for_updates(manual=False)

    def _check_for_updates_manual(self) -> None:
        self._check_for_updates(manual=True)

    def _check_for_updates(self, *, manual: bool) -> None:
        def worker() -> None:
            try:
                update = fetch_latest_release()
            except RuntimeError as exc:
                self.root.after(0, self._finish_update_check_error, str(exc), manual)
                return
            self.root.after(0, self._finish_update_check, update, manual)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_update_check_error(self, error_message: str, manual: bool) -> None:
        UIConfig.LAST_UPDATE_CHECK = int(time.time())
        UIConfig.save()
        if manual:
            show_warning(
                self.root,
                title="Update Check Failed",
                message=error_message,
            )

    def _finish_update_check(self, update, manual: bool) -> None:
        UIConfig.LAST_UPDATE_CHECK = int(time.time())
        UIConfig.save()
        current_version = self._current_version()
        if not is_newer_version(update.version, current_version):
            if manual:
                show_info(
                    self.root,
                    title="WavFix Is Up to Date",
                    message=f"You are running WavFix {current_version}.",
                    header_color=UIConfig.success_dialog_color(),
                )
            return
        if UIConfig.SKIPPED_UPDATE_VERSION == update.version and not manual:
            return

        action = show_update_available(self.root, update)
        if action == "skip":
            UIConfig.SKIPPED_UPDATE_VERSION = update.version
            UIConfig.save()

    def _build_files_tree(self) -> ttk.Treeview:
        files_tree = ttk.Treeview(
            self.input_frame,
            columns=("Filename", "Format", "Status", "Path", "Reason"),
            height=10,
            show="headings",
            style="Custom.Treeview",
        )
        files_tree.heading("Filename", text="Filename", anchor=tk.CENTER)
        files_tree.column("Filename", width=380, anchor=tk.W)
        files_tree.heading("Format", text="Format", anchor=tk.W)
        files_tree.column("Format", width=150, anchor=tk.W)
        files_tree.heading("Status", text="Process", anchor=tk.W)
        files_tree.column("Status", width=110, anchor=tk.W)
        files_tree.heading("Path", text="Path", anchor=tk.W)
        files_tree.column("Path", width=0, stretch=tk.NO, minwidth=0)
        files_tree.heading("Reason", text="Reason", anchor=tk.W)
        files_tree.column("Reason", width=0, stretch=tk.NO, minwidth=0)
        files_tree.grid(row=0, column=0, sticky="we", padx=8, pady=(1, 8))
        return files_tree

    def _build_output_text(self) -> CTkTextbox:
        output_text = CTkTextbox(
            master=self.output_frame,
            wrap="word",
            state="disabled",
            cursor="arrow",
            fg_color=UIConfig.window_color(),
            border_spacing=0,
            width=560,
            height=UIConfig.output_window_height(),
            border_width=0,
            corner_radius=0,
            activate_scrollbars=False,
            font=UIConfig.output_font(),
        )
        output_text.configure(text_color=UIConfig.output_text_color())
        output_text.grid(row=0, column=0, sticky="we", padx=8, pady=8)
        return output_text

    def _build_select_files_button(self) -> CTkButton:
        self.action_buttons_row = CTkFrame(master=self.frame, fg_color="transparent")
        self.action_buttons_row.grid(row=5, column=0, columnspan=2, sticky="we")
        self.action_buttons_row.grid_columnconfigure(0, weight=1)
        self.action_buttons_row.grid_columnconfigure(1, weight=0)
        self.action_buttons_row.grid_columnconfigure(2, weight=1)

        button = CTkButton(
            self.action_buttons_row,
            text="Select Files",
            command=self._on_select_files_clicked,
            bg_color=UIConfig.bg_color(),
            fg_color=UIConfig.button_color(),
            hover_color=UIConfig.hover_color(),
            text_color=UIConfig.button_text_color(),
            corner_radius=25,
            border_color=UIConfig.accent_color(),
            border_width=2,
            width=UIConfig.button_width(),
        )
        button.grid(row=0, column=0, sticky="w")
        return button

    def _build_settings_button(self) -> CTkButton:
        if self.action_buttons_row is None:
            self.action_buttons_row = CTkFrame(master=self.frame, fg_color="transparent")
            self.action_buttons_row.grid(row=5, column=0, columnspan=2, sticky="we")
            self.action_buttons_row.grid_columnconfigure(0, weight=1)
            self.action_buttons_row.grid_columnconfigure(1, weight=0)
            self.action_buttons_row.grid_columnconfigure(2, weight=1)

        button = CTkButton(
            master=self.action_buttons_row,
            text="Settings",
            command=self._open_settings_panel,
            width=self._settings_button_width,
            corner_radius=25,
            bg_color=UIConfig.bg_color(),
            fg_color=UIConfig.button_color(),
            hover_color=UIConfig.hover_color(),
            text_color=UIConfig.button_text_color(),
            border_color=UIConfig.accent_color(),
            border_width=2,
        )
        button.grid(row=0, column=1, padx=8, sticky="ns")
        return button

    def _build_remove_tags_button(self) -> CTkButton:
        if self.action_buttons_row is None:
            self.action_buttons_row = CTkFrame(master=self.frame, fg_color="transparent")
            self.action_buttons_row.grid(row=5, column=0, columnspan=2, sticky="we")
            self.action_buttons_row.grid_columnconfigure(0, weight=1)
            self.action_buttons_row.grid_columnconfigure(1, weight=0)
            self.action_buttons_row.grid_columnconfigure(2, weight=1)

        button = CTkButton(
            self.action_buttons_row,
            text="Clean Files",
            command=self._on_remove_tags_clicked,
            width=UIConfig.button_width(),
            bg_color=UIConfig.bg_color(),
            fg_color=UIConfig.button_color(),
            hover_color=UIConfig.hover_color(),
            text_color=UIConfig.button_text_color(),
            corner_radius=25,
            border_color=UIConfig.accent_color(),
            border_width=2,
        )
        button.grid(row=0, column=2, sticky="e")
        return button

    def _update_remove_tags_button(self) -> None:
        self._update_action_buttons()

    def _on_loading_changed(self, _is_loading: bool) -> None:
        self._update_action_buttons()

    def _on_processing_changed(self, _is_processing: bool) -> None:
        self._update_action_buttons()

    def _on_select_files_clicked(self) -> None:
        if self.file_controller.is_loading() or self.export_controller.is_processing():
            return
        self.settings_controller.close()
        self.file_controller.select_inputs()

    def _on_remove_tags_clicked(self) -> None:
        if self.file_controller.is_loading() or self.export_controller.is_processing():
            return
        self.settings_controller.close()
        self.export_controller.initiate_export()

    def _update_action_buttons(self) -> None:
        is_busy = self.file_controller.is_loading() or self.export_controller.is_processing()
        self.select_files_button.configure(state="disabled" if is_busy else "normal")
        self.settings_controller.set_busy(is_busy)

        has_files = bool(self.files_tree.get_children())
        remove_state = "normal" if (has_files and not is_busy) else "disabled"
        self.remove_tags_button.configure(state=remove_state)

    def _update_widget_colors(self) -> None:
        self.frame.configure(bg=UIConfig.bg_color())
        for widget in self.frame.winfo_children():
            if isinstance(widget, CTkButton):
                widget.configure(
                    bg_color=UIConfig.bg_color(),
                    fg_color=UIConfig.button_color(),
                    hover_color=UIConfig.hover_color(),
                    text_color=UIConfig.button_text_color(),
                    border_color=UIConfig.accent_color(),
                )
            if type(widget) is tk.Frame:
                widget.configure(bg=UIConfig.bg_color())
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(bg=UIConfig.bg_color())

        self.select_files_button.configure(
            bg_color=UIConfig.bg_color(),
            fg_color=UIConfig.button_color(),
            hover_color=UIConfig.hover_color(),
            text_color=UIConfig.button_text_color(),
            border_color=UIConfig.accent_color(),
        )
        self.remove_tags_button.configure(
            bg_color=UIConfig.bg_color(),
            fg_color=UIConfig.button_color(),
            hover_color=UIConfig.hover_color(),
            text_color=UIConfig.button_text_color(),
            border_color=UIConfig.accent_color(),
        )
        self.author_label.configure(bg=UIConfig.bg_color(), fg=UIConfig.accent_color())
        self.version_label.configure(bg=UIConfig.bg_color(), fg=UIConfig.accent_color())
        self.settings_button.configure(
            bg_color=UIConfig.bg_color(),
            fg_color=UIConfig.button_color(),
            hover_color=UIConfig.hover_color(),
            text_color=UIConfig.button_text_color(),
            border_color=UIConfig.accent_color(),
        )

        self._refresh_branding_logos()
        self.output_text.configure(fg_color=UIConfig.window_color())
        self.output_text.configure(text_color=UIConfig.output_text_color())
        self.export_controller.refresh_output_tags()
        self.input_frame.configure(
            fg_color=UIConfig.window_color(),
            border_color=UIConfig.accent_color(),
        )
        self.output_frame.configure(
            fg_color=UIConfig.window_color(),
            border_color=UIConfig.accent_color(),
        )

        self.settings_controller.apply_theme_styles()
        configure_treeview_style(self.tree_style)
        self.file_controller.refresh_tree_colors()

    def _refresh_branding_logos(self) -> None:
        self.branding_frame.configure(bg=UIConfig.bg_color(), height=self._logo_row_height)
        self.right_cluster_frame.configure(bg=UIConfig.bg_color())
        self.right_info_frame.configure(bg=UIConfig.bg_color())
        self.left_logo_label.configure(bg=UIConfig.bg_color())
        self.right_logo_label.configure(bg=UIConfig.bg_color())
        self.version_label.configure(
            bg=UIConfig.bg_color(),
            fg=UIConfig.accent_color(),
            text=self._version_text,
            image="",
        )

        left_name = "logo_dm.png" if UIConfig.DARK_MODE else "logo_lm.png"
        right_name = "logo_auragami_dm.png" if UIConfig.DARK_MODE else "logo_auragami_lm.png"

        left_logo = self._load_logo_image(left_name)
        if left_logo is not None:
            self.left_logo_label.configure(image=left_logo)
            self._left_logo_image = left_logo

        right_logo = self._load_logo_image(right_name)
        if right_logo is not None:
            self.right_logo_label.configure(image=right_logo)
            self._right_logo_image = right_logo

    def _build_resource_search_paths(self) -> list[Path]:
        paths: list[Path] = []

        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                paths.append(Path(meipass))

            exe_dir = Path(sys.executable).resolve().parent
            paths.extend(
                [
                    exe_dir,
                    exe_dir.parent,
                    exe_dir / "Resources",
                    exe_dir.parent / "Resources",
                    exe_dir.parent.parent / "Resources",
                ]
            )

        paths.extend([Path(__file__).resolve().parents[3], Path.cwd()])

        unique_paths: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            key = str(path)
            if key not in seen:
                seen.add(key)
                unique_paths.append(path)
        return unique_paths

    def _resolve_resource_path(self, relative_path: str) -> Path:
        relative = Path(relative_path)
        for base in self._resource_bases:
            candidate = base / relative
            if candidate.exists():
                return candidate
        return self._resource_bases[0] / relative

    def _load_logo_image(self, filename: str) -> tk.PhotoImage | None:
        try:
            source = self._logo_source_cache.get(filename)
            if source is None:
                source = tk.PhotoImage(file=str(self._logos_dir / filename))
                self._logo_source_cache[filename] = source

            divisor = max(1, ceil(source.height() / self._logo_row_height))
            cache_key = (filename, divisor)
            scaled = self._logo_scaled_cache.get(cache_key)
            if scaled is None:
                scaled = source.subsample(divisor, divisor)
                self._logo_scaled_cache[cache_key] = scaled
            return scaled
        except tk.TclError:
            return None

    def _read_version_text(self) -> str:
        try:
            for line in self._version_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.lower().startswith("version:"):
                    return stripped
        except OSError:
            pass
        return "Version: unknown"

    def _clear_treeview(self, _event=None) -> str:
        self.file_controller.clear_selection()
        self.files_tree.selection_remove(self.files_tree.selection())
        self.files_tree.delete(*self.files_tree.get_children())
        self._update_remove_tags_button()
        return "break"

    def _clear_output_text(self, _event=None) -> str:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.tag_remove("sel", "1.0", tk.END)
        self.output_text.configure(state="disabled")
        try:
            self.root.focus_set()
        except tk.TclError:
            pass
        return "break"

    def _clear_tree_selection_outside_input(self, event: tk.Event) -> None:
        widget = event.widget
        while widget is not None:
            if widget is self.input_frame:
                return
            widget = getattr(widget, "master", None)
        self.files_tree.selection_remove(self.files_tree.selection())

    @staticmethod
    def _warm_conversion_backend() -> None:
        threading.Thread(target=warm_conversion_backend, daemon=True).start()

    def _on_close(self) -> None:
        UIConfig.save()
        self.settings_controller.close(revert_preview=False)
        self.root.destroy()

    def _quit_bindings(self) -> None:
        if UIConfig.os_name == "Darwin":
            self.root.bind_all("<Command-Q>", lambda _event: self._on_close())
            self.root.createcommand("::tk::mac::Quit", self._on_close)
        elif UIConfig.os_name == "Windows":
            self.root.bind_all("<Alt-F4>", lambda _event: self._on_close())
            self.root.bind_all("<Control-q>", lambda _event: self._on_close())
        elif UIConfig.os_name == "Linux":
            self.root.bind_all("<Control-q>", lambda _event: self._on_close())

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = WavFixApp()
    app.run()
