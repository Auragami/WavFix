"""Treeview style helpers for the WavFix UI."""

from __future__ import annotations

import platform
from tkinter import ttk

from ..theme import UIConfig


def create_treeview_style() -> ttk.Style:
    """Create and configure the custom treeview style."""
    style = ttk.Style()
    if platform.system() == "Windows":
        style.theme_use("default")

    style.element_create("Custom.Treeview.Heading", "from", "default")
    style.layout(
        "Custom.Treeview.Heading",
        [
            (
                "Custom.Treeview.Heading.cell",
                {
                    "sticky": "nswe",
                    "children": [
                        (
                            "Custom.Treeview.Heading.padding",
                            {
                                "sticky": "nswe",
                                "children": [
                                    (
                                        "Custom.Treeview.Heading.image",
                                        {"side": "right", "sticky": "e"},
                                    ),
                                    (
                                        "Custom.Treeview.Heading.text",
                                        {"sticky": "nswe"},
                                    ),
                                ],
                            },
                        )
                    ],
                },
            )
        ],
    )
    configure_treeview_style(style)
    return style


def configure_treeview_style(style: ttk.Style) -> None:
    """Apply current theme colors/fonts to the custom treeview style."""
    style.configure(
        "Custom.Treeview.Heading",
        background=UIConfig.bg_color(),
        foreground=UIConfig.header_text_color(),
        font=UIConfig.header_text(),
        borderwidth=0,
        relief="flat",
        padding=(4, 0, 0, 0),
    )
    style.map(
        "Custom.Treeview.Heading",
        background=[("active", UIConfig.hover_color())],
        relief=[("pressed", "flat"), ("!pressed", "flat")],
    )
    style.configure("Treeview.Column", anchor="w")
    style.map(
        "Treeview",
        background=[
            ("selected", "focus", UIConfig.button_color()),
            ("selected", "!focus", UIConfig.button_color()),
        ],
        foreground=[
            ("selected", "focus", UIConfig.button_text_color()),
            ("selected", "!focus", UIConfig.button_text_color()),
        ],
    )
    style.configure(
        "Treeview",
        font=UIConfig.treeview_text(),
        fieldbackground=UIConfig.window_color(),
        background=UIConfig.window_color(),
        borderwidth=0,
    )
