"""Segmented-control widget used across the WavFix UI."""

from __future__ import annotations

from collections.abc import Callable

from customtkinter import CTkButton, CTkFrame

from ..theme import UIConfig


class SegmentedControl:
    """Custom segmented control with deterministic click behavior on macOS."""

    def __init__(
        self,
        master,
        *,
        values: list[str],
        width: int,
        command: Callable[[str], None] | None = None,
    ) -> None:
        self.widget = CTkFrame(master=master, fg_color="transparent")
        self._values = list(values)
        self._command = command
        self._selected = self._values[0] if self._values else ""
        self._palette = UIConfig.segmented_palette()
        self._buttons: dict[str, CTkButton] = {}

        segment_width = max(90, width // max(1, len(self._values)))
        for index, value in enumerate(self._values):
            self.widget.grid_columnconfigure(index, weight=1)
            button = CTkButton(
                master=self.widget,
                text=value,
                width=segment_width,
                height=32,
                corner_radius=6,
                border_width=2,
                command=lambda current=value: self._on_select(current),
            )
            button.grid(row=0, column=index, padx=(0, 4 if index < len(self._values) - 1 else 0))
            self._buttons[value] = button

        self.apply_palette(self._palette)

    def grid(self, **kwargs) -> None:
        self.widget.grid(**kwargs)

    def set(self, value: str) -> None:
        if value not in self._buttons:
            return
        self._selected = value
        self._refresh_buttons()

    def get(self) -> str:
        return self._selected

    def configure(self, *, state: str) -> None:
        for button in self._buttons.values():
            button.configure(state=state)

    def apply_palette(self, palette: dict[str, str]) -> None:
        self._palette = palette
        self._refresh_buttons()

    def _on_select(self, value: str) -> None:
        self.set(value)
        if self._command is not None:
            self._command(value)

    def _refresh_buttons(self) -> None:
        for value, button in self._buttons.items():
            selected = value == self._selected
            button.configure(
                fg_color=(
                    self._palette["selected_color"]
                    if selected
                    else self._palette["unselected_color"]
                ),
                hover_color=(
                    self._palette["selected_hover_color"]
                    if selected
                    else self._palette["unselected_hover_color"]
                ),
                text_color=self._palette["text_color"],
                border_color=self._palette["border_color"],
            )
