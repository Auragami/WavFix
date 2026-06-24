"""Drag-and-drop behavior for WavFix UI."""

from __future__ import annotations

import tkinter as tk

from ..controllers.file_tree_controller import FileTreeController


class DnDHandler:
    """Handles drag and drop events for files and folders."""

    def __init__(self, file_controller: FileTreeController, root: tk.Tk):
        self.file_controller = file_controller
        self.root = root

    def __call__(self, event):
        dropped_items = self.root.tk.splitlist(event.data)
        self.file_controller.load_selected_items(list(dropped_items), origin="dnd")

        return event.action
