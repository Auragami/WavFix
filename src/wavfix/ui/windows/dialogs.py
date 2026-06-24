"""Small custom dialogs for warning flows that need themed presentation."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from collections.abc import Callable
from typing import Literal, overload

from customtkinter import CTkButton, CTkCheckBox, CTkFrame, CTkLabel

from ...core.update_checker import UpdateInfo
from ..theme import UIConfig

FFMPEG_DOWNLOAD_URL = "https://ffmpeg.org/download.html"


def _dialog_text_color() -> str:
    return UIConfig.accent_color()


def _center_on_parent(window: tk.Toplevel, parent: tk.Tk) -> None:
    parent.update_idletasks()
    window.update_idletasks()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    window.geometry(f"+{x}+{y}")


def _base_dialog(parent: tk.Tk, title: str) -> tk.Toplevel:
    window = tk.Toplevel(parent)
    window.withdraw()
    window.title(title)
    window.transient(parent)
    window.resizable(False, False)
    window.configure(bg=UIConfig.window_color())
    window.grid_columnconfigure(0, weight=1)
    return window


def show_warning(parent: tk.Tk, *, title: str, message: str) -> None:
    """Show a themed warning dialog with a red header."""

    window = _base_dialog(parent, title)
    panel = CTkFrame(
        master=window,
        fg_color=UIConfig.bg_color(),
        border_color=UIConfig.red_files_color(),
        border_width=2,
        corner_radius=10,
    )
    panel.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    panel.grid_columnconfigure(0, weight=1)

    CTkLabel(
        master=panel,
        text=title,
        font=("Roboto", 13, "bold"),
        fg_color="transparent",
        text_color=UIConfig.red_files_color(),
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
    CTkLabel(
        master=panel,
        text=message,
        font=("Roboto", 11, "normal"),
        fg_color="transparent",
        text_color=_dialog_text_color(),
        justify="left",
        wraplength=360,
    ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 12))

    ok_button = CTkButton(
        master=panel,
        text="OK",
        width=120,
        corner_radius=14,
        command=window.destroy,
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    ok_button.grid(row=2, column=0, padx=12, pady=(0, 12))

    _center_on_parent(window, parent)
    window.deiconify()
    window.lift()
    window.focus_set()
    ok_button.focus_set()
    parent.wait_window(window)


def show_info(
    parent: tk.Tk,
    *,
    title: str,
    message: str,
    header_color: str | None = None,
) -> None:
    """Show a themed informational dialog."""

    window = _base_dialog(parent, title)
    status_color = header_color or UIConfig.accent_color()
    panel = CTkFrame(
        master=window,
        fg_color=UIConfig.bg_color(),
        border_color=status_color,
        border_width=2,
        corner_radius=10,
    )
    panel.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    panel.grid_columnconfigure(0, weight=1)

    CTkLabel(
        master=panel,
        text=title,
        font=("Roboto", 13, "bold"),
        fg_color="transparent",
        text_color=status_color,
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
    CTkLabel(
        master=panel,
        text=message,
        font=("Roboto", 11, "normal"),
        fg_color="transparent",
        text_color=_dialog_text_color(),
        justify="left",
        wraplength=360,
    ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 12))

    ok_button = CTkButton(
        master=panel,
        text="OK",
        width=120,
        corner_radius=14,
        command=window.destroy,
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    ok_button.grid(row=2, column=0, padx=12, pady=(0, 12))

    _center_on_parent(window, parent)
    window.deiconify()
    window.lift()
    window.focus_set()
    ok_button.focus_set()
    parent.wait_window(window)


@overload
def ask_warning_yes_no(
    parent: tk.Tk,
    *,
    title: str,
    message: str,
    show_do_not_show_again: Literal[False] = False,
) -> bool: ...


@overload
def ask_warning_yes_no(
    parent: tk.Tk,
    *,
    title: str,
    message: str,
    show_do_not_show_again: Literal[True],
) -> tuple[bool, bool]: ...


def ask_warning_yes_no(
    parent: tk.Tk,
    *,
    title: str,
    message: str,
    show_do_not_show_again: bool = False,
) -> bool | tuple[bool, bool]:
    """Ask a yes/no warning question with an optional persistence checkbox."""

    result = {"answer": False}
    dont_show_again = tk.BooleanVar(value=False)
    window = _base_dialog(parent, title)
    panel = CTkFrame(
        master=window,
        fg_color=UIConfig.bg_color(),
        border_color=UIConfig.red_files_color(),
        border_width=2,
        corner_radius=10,
    )
    panel.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_columnconfigure(1, weight=1)

    CTkLabel(
        master=panel,
        text=title,
        font=("Roboto", 13, "bold"),
        fg_color="transparent",
        text_color=UIConfig.red_files_color(),
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))
    CTkLabel(
        master=panel,
        text=message,
        font=("Roboto", 11, "normal"),
        fg_color="transparent",
        text_color=_dialog_text_color(),
        justify="left",
        wraplength=420,
    ).grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))

    button_row = 2
    if show_do_not_show_again:
        checkbox = CTkCheckBox(
            master=panel,
            text="Do not show this again",
            variable=dont_show_again,
            fg_color=UIConfig.button_color(),
            hover_color=UIConfig.hover_color(),
            text_color=_dialog_text_color(),
            border_color=UIConfig.accent_color(),
            border_width=2,
        )
        checkbox.grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))
        button_row = 3

    def choose(answer: bool) -> None:
        result["answer"] = answer
        window.destroy()

    no_button = CTkButton(
        master=panel,
        text="No",
        width=120,
        corner_radius=14,
        command=lambda: choose(False),
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    yes_button = CTkButton(
        master=panel,
        text="Yes",
        width=120,
        corner_radius=14,
        command=lambda: choose(True),
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    no_button.grid(row=button_row, column=0, sticky="we", padx=(12, 5), pady=(0, 12))
    yes_button.grid(row=button_row, column=1, sticky="we", padx=(5, 12), pady=(0, 12))

    window.protocol("WM_DELETE_WINDOW", lambda: choose(False))
    _center_on_parent(window, parent)
    window.deiconify()
    window.lift()
    window.focus_set()
    yes_button.focus_set()
    parent.wait_window(window)
    if show_do_not_show_again:
        return result["answer"], dont_show_again.get()
    return result["answer"]


def show_ffmpeg_recommendation(
    parent: tk.Tk,
    *,
    on_do_not_show_again: Callable[[], None],
) -> None:
    """Explain how to install FFmpeg when the optional FFmpeg backend is selected."""

    window = _base_dialog(parent, "FFmpeg Not Found")
    dont_show_again = tk.BooleanVar(value=False)

    panel = CTkFrame(
        master=window,
        fg_color=UIConfig.bg_color(),
        border_color=UIConfig.red_files_color(),
        border_width=2,
        corner_radius=10,
    )
    panel.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    panel.grid_columnconfigure(0, weight=1)

    CTkLabel(
        master=panel,
        text="FFmpeg Not Found",
        font=("Roboto", 13, "bold"),
        fg_color="transparent",
        text_color=UIConfig.red_files_color(),
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
    CTkLabel(
        master=panel,
        text=(
            "FFmpeg conversion is enabled, but WavFix could not find FFmpeg.\n\n"
            "FFmpeg is free. Install it from the official site, choose an FFmpeg "
            "executable in Settings, or switch Converter back to Built-in."
        ),
        font=("Roboto", 11, "normal"),
        fg_color="transparent",
        text_color=_dialog_text_color(),
        justify="left",
        wraplength=420,
    ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

    link = tk.Label(
        master=panel,
        text="Official FFmpeg download page",
        bg=UIConfig.bg_color(),
        fg=UIConfig.blue_files_color(),
        cursor="hand2",
        font=("Roboto", 11, "underline"),
    )
    link.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))
    link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(FFMPEG_DOWNLOAD_URL))

    checkbox = CTkCheckBox(
        master=panel,
        text="Do not show this again",
        variable=dont_show_again,
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=_dialog_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    checkbox.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 12))

    def close() -> None:
        if dont_show_again.get():
            on_do_not_show_again()
        window.destroy()

    ok_button = CTkButton(
        master=panel,
        text="Continue",
        width=140,
        corner_radius=14,
        command=close,
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    ok_button.grid(row=4, column=0, sticky="e", padx=12, pady=(0, 12))

    window.protocol("WM_DELETE_WINDOW", close)
    _center_on_parent(window, parent)
    window.deiconify()
    window.lift()
    window.focus_set()
    ok_button.focus_set()
    parent.wait_window(window)


def show_update_available(parent: tk.Tk, update: UpdateInfo) -> str:
    """Show update details and return download/later/skip."""

    result = {"action": "later"}
    window = _base_dialog(parent, "WavFix Update Available")

    panel = CTkFrame(
        master=window,
        fg_color=UIConfig.bg_color(),
        border_color=UIConfig.orange_files_color(),
        border_width=2,
        corner_radius=10,
    )
    panel.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_columnconfigure(1, weight=1)
    panel.grid_columnconfigure(2, weight=1)

    CTkLabel(
        master=panel,
        text=f"WavFix {update.version} is available",
        font=("Roboto", 13, "bold"),
        fg_color="transparent",
        text_color=UIConfig.orange_files_color(),
    ).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12, 6))

    notes = update.notes.strip()
    if len(notes) > 700:
        notes = f"{notes[:700].rstrip()}\n..."
    if not notes:
        notes = "A newer WavFix release is available."

    CTkLabel(
        master=panel,
        text=notes,
        font=("Roboto", 11, "normal"),
        fg_color="transparent",
        text_color=_dialog_text_color(),
        justify="left",
        wraplength=520,
    ).grid(row=1, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 12))

    def choose(action: str) -> None:
        result["action"] = action
        if action == "download":
            webbrowser.open_new_tab(update.release_url)
        window.destroy()

    later_button = CTkButton(
        master=panel,
        text="Later",
        corner_radius=14,
        command=lambda: choose("later"),
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    skip_button = CTkButton(
        master=panel,
        text="Skip Version",
        corner_radius=14,
        command=lambda: choose("skip"),
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    download_button = CTkButton(
        master=panel,
        text="Download",
        corner_radius=14,
        command=lambda: choose("download"),
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    later_button.grid(row=2, column=0, sticky="we", padx=(12, 5), pady=(0, 12))
    skip_button.grid(row=2, column=1, sticky="we", padx=5, pady=(0, 12))
    download_button.grid(row=2, column=2, sticky="we", padx=(5, 12), pady=(0, 12))

    window.protocol("WM_DELETE_WINDOW", lambda: choose("later"))
    _center_on_parent(window, parent)
    window.deiconify()
    window.lift()
    window.focus_set()
    download_button.focus_set()
    parent.wait_window(window)
    return result["action"]
