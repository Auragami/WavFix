"""Tooltip behavior used across WavFix UI widgets."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
from typing import cast

from ..theme import UIConfig


class ToolTip:
    """Creates a tooltip for a given widget."""

    treeview_font = UIConfig.treeview_text()

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.after_id: str | None = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        if isinstance(self.widget, ttk.Treeview):
            self.widget.bind("<Motion>", self.on_motion)
        self.current_target: tuple[str, str] | None = None
        self._last_motion_ts = 0.0
        self._last_motion_xy: tuple[int, int] = (-1, -1)
        self._motion_interval_s = 0.04

    def _get_item_text_and_width(self, item):
        item_text = self.widget.item(item, "values")
        if item_text and item_text[0]:
            text = item_text[0]
            font = ToolTip.treeview_font
            text_width = self.widget.winfo_toplevel().tk.call("font", "measure", font, text)
            return text, text_width
        return None, None

    def _get_cell_text_width(self, values: tuple[str, ...], column: str):
        column_index_by_id = {"#1": 0, "#2": 1, "#3": 2}
        value_index = column_index_by_id.get(column)
        if value_index is None or len(values) <= value_index:
            return None
        cell_text = values[value_index]
        if not cell_text:
            return None
        font = ToolTip.treeview_font
        text_width = self.widget.winfo_toplevel().tk.call("font", "measure", font, cell_text)
        return int(text_width)

    def _resolve_treeview_tooltip(self, event):
        item = self.widget.identify_row(
            self.widget.winfo_pointerxy()[1] - self.widget.winfo_rooty()
        )
        column = self.widget.identify_column(
            self.widget.winfo_pointerxy()[0] - self.widget.winfo_rootx()
        )
        if not item:
            return None

        values = cast(tuple[str, ...], self.widget.item(item, "values"))
        path_text = values[3] if len(values) > 3 else ""
        reason_text = values[4] if len(values) > 4 else ""
        bbox = self.widget.bbox(item, column)
        if not bbox:
            return None
        x1, y1, width, _ = bbox

        tooltip_text = ""
        x = int(cast(int, x1)) + self.widget.winfo_rootx() + 10
        y = int(cast(int, y1)) + self.widget.winfo_rooty() + 2

        if column == "#1":
            text_width = self._get_cell_text_width(values, column)
            if not text_width:
                return None
            if not (x1 < event.x < x1 + text_width):
                return None
            tooltip_text = path_text
            x = int(cast(int, x1)) + int(text_width) + self.widget.winfo_rootx() + 10
        elif column in ("#2", "#3"):
            text_width = self._get_cell_text_width(values, column)
            if not text_width:
                return None
            if not (x1 < event.x < x1 + text_width):
                return None
            if not reason_text:
                return None
            tooltip_text = reason_text
            x = int(cast(int, x1)) + int(text_width) + self.widget.winfo_rootx() + 10
        else:
            return None

        if not tooltip_text.strip():
            return None

        return item, column, tooltip_text, x, y

    def on_motion(self, event):
        if isinstance(self.widget, ttk.Treeview):
            now = time.monotonic()
            current_xy = (int(event.x), int(event.y))
            if (
                current_xy == self._last_motion_xy
                and (now - self._last_motion_ts) < self._motion_interval_s
            ):
                return
            if (now - self._last_motion_ts) < self._motion_interval_s:
                return
            self._last_motion_ts = now
            self._last_motion_xy = current_xy

            resolved = self._resolve_treeview_tooltip(event)
            if resolved is not None:
                item, column, _, _, _ = resolved
                target = (item, column)
                if target != self.current_target:
                    self.hide_tooltip(event)
                    self.current_target = target
                    self.schedule_tooltip(event)
            else:
                self.hide_tooltip(event)
                self.current_target = None

    def schedule_tooltip(self, _event):
        if self.tooltip_window:
            return

        if self.after_id:
            self.widget.after_cancel(self.after_id)

        self.after_id = self.widget.after(450, self.show_tooltip)

    def show_tooltip(self):
        if isinstance(self.widget, ttk.Treeview):
            pointer_x = self.widget.winfo_pointerxy()[0] - self.widget.winfo_rootx()
            pointer_y = self.widget.winfo_pointerxy()[1] - self.widget.winfo_rooty()
            event = tk.Event()
            event.x = int(pointer_x)
            event.y = int(pointer_y)

            resolved = self._resolve_treeview_tooltip(event)
            if resolved is None:
                return
            _, _, tooltip_text, x, y = resolved
        else:
            tooltip_text = self.text
            try:
                x0, y0, _, _ = self.widget.bbox("insert")
                x = int(cast(int, x0)) + self.widget.winfo_rootx() + 15
                y = int(cast(int, y0)) + self.widget.winfo_rooty() + 40
            except Exception:
                x = self.widget.winfo_rootx() + 12
                y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window,
            text=tooltip_text,
            relief="flat",
            borderwidth=1,
            font=("Roboto", 10, "normal"),
            background="white",
            fg="black",
            padx=2,
            pady=1,
        )
        label.pack()

    def hide_tooltip(self, _event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
