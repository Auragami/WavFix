# Copyright (C) 2023 Dreamwalker

# This file is part of WavFix.

# WavFix is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# WavFix is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with WavFix.  If not, see <http://www.gnu.org/licenses/>.

import os
import platform
import shutil
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from customtkinter import CTkButton, CTkLabel, CTkTextbox
from tkinterdnd2 import DND_FILES, TkinterDnD


class UIConfig:
    """UI configuration class for color themes and styling."""
    # Get the operating system
    os_name = platform.system()

    # Color Methods
    DARK_MODE = False

    @staticmethod
    def bg_color():
        return "#191919" if UIConfig.DARK_MODE else "#E0E0E0"

    @staticmethod
    def accent_color():
        return "#9F9F9F" if UIConfig.DARK_MODE else "#333333"

    @staticmethod
    def window_color():
        return "#0F0F0F" if UIConfig.DARK_MODE else "#2E2E2E"

    @staticmethod
    def header_text_color():
        return "#9F9F9F" if UIConfig.DARK_MODE else "white"

    @staticmethod
    def button_color():
        return "#373737" if UIConfig.DARK_MODE else "#5D5D5D"

    @staticmethod
    def button_text_color():
        return "#EBEBEB" if UIConfig.DARK_MODE else "white"

    @staticmethod
    def hover_color():
        return "#656565" if UIConfig.DARK_MODE else "#7D7D7D"

    @staticmethod
    def blue_files_color():
        return "#1E90FF" if UIConfig.DARK_MODE else "#3A9BFF"

    @staticmethod
    def green_files_color():
        return "#00A300" if UIConfig.DARK_MODE else "#39E639"

    @staticmethod
    def red_files_color():
        return "#B22222" if UIConfig.DARK_MODE else "#E63939"
    
    # Main Window Methods
    @staticmethod
    def header_text():
        # Adjust the font size based on the operating system
        header_font_size = 12 if UIConfig.os_name == "Darwin" else 9
        header_font = ("Roboto", header_font_size, "bold")
        return header_font
    
    @staticmethod
    def treeview_text():
        # Adjust the font size based on the operating system   
        treeview_font_size = 14 if UIConfig.os_name == "Darwin" else 11
        treeview_font = ("Roboto", treeview_font_size, "normal")
        return treeview_font
    
    @staticmethod
    def create_custom_treeview_style():
        """Create a custom style for the Treeview widget."""
        style = ttk.Style()
        if platform.system() == "Windows":
            style.theme_use("default")

        style.element_create("Custom.Treeview.Heading", "from", "default")
        style.layout(
            "Custom.Treeview.Heading",
            [
                ("Custom.Treeview.Heading.cell", {"sticky": "nswe"}),
                (
                    "Custom.Treeview.Heading.border",
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
                                            {"side": "top", "sticky": ""},
                                        ),
                                        (
                                            "Custom.Treeview.Heading.text",
                                            {"side": "top", "sticky": ""},
                                        ),
                                    ],
                                },
                            )
                        ],
                    },
                ),
            ],
        )
        return style

    @staticmethod
    def configure_treeview_style(style, config,):
        """Configure the appearance of the Treeview widget."""

        style.configure(
            "Custom.Treeview.Heading",
            background=config.bg_color(),
            foreground=config.header_text_color(),
            font=config.header_text(),
        )

        style.map(
            "Custom.Treeview.Heading",
            background=[("active", config.hover_color())],
            relief=[("pressed", "flat")],
        )
        
        style.map(
            "Custom.Treeview.Heading",
            background=[("active", config.hover_color())],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )

        style.configure("Treeview.Column", anchor="w")

        # Set focus color to match unfocused color
        style.map(
            "Treeview",
            background=[
                ("selected", "focus", config.window_color()),
                ("selected", "!focus", config.window_color()),
            ],
            foreground=[
                ("selected", "focus", config.window_color()),
                ("selected", "!focus", config.window_color()),
            ],
        )

        style.configure(
            "Treeview",
            font=config.treeview_text(),
            fieldbackground=config.window_color(),
            background=config.window_color(),
            borderwidth=0,
        )

    # Output Window Methods
    @staticmethod
    def output_text_color():
        return "#00A300" if UIConfig.DARK_MODE else "#33CC33"
    
    @staticmethod
    def output_font():
        """Get the operating system and set the output font accordingly"""
        os_name = UIConfig.os_name
        if os_name == "Darwin":
            output_font = ("Menlo", 11) 
        elif os_name == "Windows":
            output_font = ("Consolas", 12)
        else: 
            output_font = ("DejaVu Sans Mono", 12)
            
        return output_font

    @staticmethod
    def output_window_height():
        os_name = UIConfig.os_name
        if os_name == "Darwin":
            return 80
        else:
            return 86
        
    @staticmethod
    def window_curves():
        return 0

    # Button Methods
    @staticmethod
    def button_width():
        return 140

    @staticmethod
    def button_curves():
        return 25
    
    # Theme Methods
    @staticmethod
    def toggle_dark_mode(event=None, style=None):
        """Toggles the state of the color theme"""
        UIConfig.DARK_MODE = not UIConfig.DARK_MODE
        UIConfig.update_widget_colors(style)

    @staticmethod
    def update_treeview_colors():
        """Updates the color of the files text in the treeview"""
        for item in files_tree.get_children():
            file_path = files_tree.set(item, "Path")
            bytes_20_21 = FileHandler.read_wav_file(Path(file_path))

            color = FileHandler.get_color(Path(file_path), bytes_20_21)
            files_tree.item(item, tags=(color,))
            files_tree.tag_configure(color, foreground=color)

    @staticmethod
    def update_widget_colors(style):
        """Updates the colors of the UI elements"""
        frame.configure(bg=UIConfig.bg_color())

        for widget in frame.winfo_children():
            if isinstance(widget, CTkButton):
                widget.configure(
                    bg_color=UIConfig.bg_color(),
                    fg_color=UIConfig.button_color(),
                    hover_color=UIConfig.hover_color(),
                    text_color=UIConfig.button_text_color(),
                    border_color=UIConfig.accent_color(),
                )

            if isinstance(widget, CTkLabel):
                widget.configure(fg_color=UIConfig.bg_color(), text_color=UIConfig.accent_color())

        good_bad_label.configure(text_color=UIConfig.green_files_color())
        bad_label.configure(text_color=UIConfig.red_files_color())

        files_tree.tag_configure("oddrow", background=UIConfig.window_color())
        files_tree.tag_configure("evenrow", background=UIConfig.bg_color())

        output_text.configure(fg_color=UIConfig.window_color())
        output_text.configure(text_color=UIConfig.output_text_color())

        UIConfig.update_treeview_colors()
        UIConfig.configure_treeview_style(style, UIConfig)


class FileHandler:
    """Class for handling files and folders."""

    SUPPORTED_EXTENSIONS = (
        ".aiff",
        ".flac",
        ".m4a",
        ".mp3",
        ".ogg",
        ".raw",
        ".wav",
        ".jpg",
        ".jpeg",
        ".png",
        ".txt",
        ".pdf",
    )
    accepted_extensions = set(SUPPORTED_EXTENSIONS)  # For more efficient lookup

    def __init__(self, files_tree, batch_mode, update_remove_tags_button, root):
        self.files_tree = files_tree
        self.batch_mode = batch_mode
        self.update_remove_tags_button = update_remove_tags_button
        self.root = root

    @staticmethod
    def file_extension_checker(file_path):
        """Check if the file extension is supported by the application."""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in FileHandler.accepted_extensions

    def select_files(self):
        """Open a browser to select files and add them to the treeview"""
        previous_batch_mode = self.batch_mode
        self.batch_mode = False
        file_extensions = FileHandler.accepted_extensions
        file_types = (
            "Common Album Files",
            " ".join("*" + ext for ext in file_extensions),
        )

        file_paths = filedialog.askopenfilenames(filetypes=[file_types])

        if not file_paths:
            self.batch_mode = previous_batch_mode
            return

        self.add_files_to_tree(file_paths)
        self.root.focus_force()

    def select_folder(self, input_directory=None):
        """Batch-select files for processing and return their paths.

        Args:
            input_directory (str, optional): The path of the directory containing the files. Defaults to None.

        Returns:
            list: A list of file paths.
        """
        previous_batch_mode = self.batch_mode
        self.batch_mode = True

        if not input_directory:
            input_directory = filedialog.askdirectory()

            if not input_directory:
                self.batch_mode = previous_batch_mode
                return

        input_directory = os.path.abspath(input_directory)

        file_paths = []

        for root_dir, _, files in os.walk(input_directory):
            for file in files:
                if file.startswith("._"):
                    continue
                if not FileHandler.file_extension_checker(file):
                    continue

                input_file = os.path.join(root_dir, file)
                file_paths.append(input_file)

        self.add_files_to_tree(file_paths)

    @staticmethod
    def read_wav_file(input_file):
        """Read a WAV file and return bytes 20 and 21 as a tuple, or None if invalid or not a WAV file."""
        ext = input_file.suffix.lower()
        if ext != ".wav":
            return None

        try:
            with open(input_file, "rb") as f_in:
                data = f_in.read()
                if len(data) >= 22:
                    return data[20:22]
                else:
                    return None
        except (OSError, IOError) as e:
            tk.messagebox.showerror(
                "Error", f"Error reading the file {input_file}: {e}"
            )
            return None

    @staticmethod
    def get_color(file_path, bytes_20_21):
        """Retrieve the color information for a file based on the specified bytes.

        - WAV files with bytes 20 and 21 equal to 01 00 are colored green.
        - WAV files with bytes 20 and 21 not equal to 01 00 are colored red.
        - Non-WAV files are colored blue.

        Args:
            file_path: The path of the file to read the color information from.
            bytes_20_21: A tuple containing the byte positions to be read.

        Returns:
            str: The color information extracted from the file.
        """
        ext = file_path.suffix.lower()
        if ext == ".wav":
            if bytes_20_21 and bytes_20_21[0] == 1 and bytes_20_21[1] == 0:
                return UIConfig.green_files_color()
            else:
                return UIConfig.red_files_color()
        else:
            return UIConfig.blue_files_color()

    def add_files_to_tree(self, file_paths):
        """Add files to the treeview with the corresponding color based on the type."""
        if not file_paths:
            return

        self.files_tree.delete(*self.files_tree.get_children())  # Refresh the treeview

        for file_path in file_paths:
            if not FileHandler.file_extension_checker(file_path):
                continue

            file_path = Path(file_path)
            bytes_20_21 = self.read_wav_file(file_path)
            color = self.get_color(file_path, bytes_20_21)

            if bytes_20_21:
                bytes_str = f"{bytes_20_21[0]:02X} {bytes_20_21[1]:02X}"
            else:
                bytes_str = ""

            file_name = file_path.name

            padding_spaces = " " * int(
                (self.files_tree.column("Bytes", "width") - 6 * len(bytes_str))
                // 2
                // 5
            )
            bytes_str_padded = f"{padding_spaces}{bytes_str}"

            self.files_tree.insert(
                "",
                "end",
                values=(file_name, bytes_str_padded, str(file_path)),
                tags=(color,),
            )
            self.files_tree.tag_configure(color, foreground=color)
            self.update_remove_tags_button()

        if self.files_tree.get_children():
            self.files_tree.see(
                self.files_tree.get_children()[-1]
            )  # Make sure the last item is visible
            self.update_remove_tags_button()

        self.root.focus_force()

    @staticmethod
    def update_remove_tags_button():
        """Check for items in the tree view, disable button if there are none."""
        if files_tree.get_children():
            remove_tags_button.configure(state="normal")
        else:
            remove_tags_button.configure(state="disabled")


class FileProcessor:
    def __init__(self, files_tree, batch_mode, root):
        self.files_tree = files_tree
        self.batch_mode = batch_mode
        self.root = root

        self.output_directory = None
        self.file_paths = None
        self.parent_directory = None
        self.parent_directory_name = None
        self.existing_items = None
        self.user_choice = None

    def get_output_directory(self):
        """Get the output directory for the selected files."""
        self.output_directory = filedialog.askdirectory(title="Select Output Directory")

    def get_file_paths(self):
        """Get the file paths for the selected files."""
        self.file_paths = [
            Path(self.files_tree.set(item, "Path"))
            for item in self.files_tree.get_children()
        ]

    def get_common_parent_directory(self):
        """Get the common parent directory for the selected files."""
        common_prefix = os.path.commonprefix(self.file_paths)
        self.parent_directory = os.path.dirname(common_prefix)
        self.parent_directory_name = os.path.basename(self.parent_directory)

    def get_existing_items(self):
        """Get the existing items for the selected files."""
        self.existing_items = os.listdir(self.output_directory)

    def get_output_file_batch_mode(self, file_path):
        """Get the output file for the selected files in batch mode."""
        relative_path = os.path.relpath(file_path, self.parent_directory)
        output_directory_with_subdir = os.path.join(
            self.output_directory, self.parent_directory_name
        )

        if (
            self.parent_directory_name in self.existing_items
            and self.user_choice is None
        ):
            self.user_choice = messagebox.askyesno(
                title="Overwrite folder?",
                message=f"Do you want to overwrite the existing folder '{self.parent_directory_name}'?",
            )

        if not self.user_choice and self.parent_directory_name in self.existing_items:
            output_directory_with_subdir += "_clean"

        output_file = os.path.join(output_directory_with_subdir, relative_path)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        return output_file

    def get_output_file_single_mode(self, input_file_name):
        """Get the output file for the selected files in single mode."""
        output_file = os.path.join(self.output_directory, input_file_name)

        if input_file_name in self.existing_items and self.user_choice is None:
            self.user_choice = messagebox.askyesno(
                title="Overwrite files?",
                message="Do you want to overwrite existing files?",
            )

        if not self.user_choice and input_file_name in self.existing_items:
            output_file = os.path.join(
                self.output_directory, input_file_name.replace(".", "_clean.")
            )

        return output_file

    def process_file(self, file_path, output_file):
        """Process a wav file"""
        if (
            file_path.absolute().as_posix().casefold()
            == Path(output_file).absolute().as_posix().casefold()
        ):
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_output_file = temp_file.name

            self.edit_wav_file(file_path, temp_output_file)
            shutil.move(temp_output_file, output_file)
        else:
            self.edit_wav_file(file_path, output_file)

        self.update_status(f"\nModified file saved to: {output_file}")

    def process_selected_files(self):
        """Process the selected files in batch mode or single mode."""
        self.get_output_directory()

        if not self.output_directory:
            return

        self.get_file_paths()
        self.get_common_parent_directory()
        self.get_existing_items()

        for file_path in self.file_paths:
            input_file_name = os.path.basename(file_path)

            if self.batch_mode:
                output_file = self.get_output_file_batch_mode(file_path)
            else:
                output_file = self.get_output_file_single_mode(input_file_name)

            self.process_file(file_path, output_file)

        self.update_status("\n\nDone!")
        self.root.focus_force()

    @staticmethod
    def edit_wav_file(input_file, output_file):
        """Edit a WAV file if it has the wFormatTag, to set bytes 20-21 to a value of 01 00, or copy the file."""
        ext = input_file.suffix.lower()
        if ext == ".wav":
            wav_bytes_20_21 = FileHandler.read_wav_file(input_file)
            if wav_bytes_20_21 != b'\x01\x00':
                with open(input_file, "rb") as f_in:
                    data = f_in.read()

                # Modify the wFormatTag (bytes 20-21) to a value of 01 00
                modified_data = bytearray(data)
                modified_data[20] = 1
                modified_data[21] = 0

                with open(output_file, "wb") as f_out:
                    f_out.write(modified_data)
            else:
                shutil.copy(input_file, output_file)
        else:
            shutil.copy(input_file, output_file)

    @staticmethod
    def update_status(status_text):
        """Enables the output window and inserts status updates to it."""
        output_text.configure(state="normal")
        output_text.insert(tk.END, status_text)
        output_text.see(tk.END)
        output_text.configure(state="disabled")
        output_text.update()


class DnDHandler(object):
    """Handles drag and drop events for the Main window.

    When a file or directory is dropped, this class separates the dropped items into files and directories,
    and processes them accordingly by either adding the files to the tree or processing the directories in batch mode.
    """

    def __init__(self, file_handler):
        self.file_handler = file_handler

    def __call__(self, event):
        dropped_items = root.tk.splitlist(event.data)

        # Separate dropped files and directories
        dropped_files = []
        dropped_directories = []
        for item in dropped_items:
            if os.path.isfile(item):
                dropped_files.append(item)
            elif os.path.isdir(item):
                dropped_directories.append(item)

        # If any directories were dropped, process them using the select_folder function
        if dropped_directories:
            for directory in dropped_directories:
                self.file_handler.select_folder(input_directory=directory)

        # If any files were dropped, add them to the tree
        if dropped_files:
            self.file_handler.batch_mode = False
            self.file_handler.add_files_to_tree(dropped_files)

        return event.action


def initiate_export():  # Instanced on call so updates from FileProcessor are ensured.
    """Creates an instance of the FileProcessor class to pass files through the smart-save logic."""
    file_processor = FileProcessor(files_tree, file_handler.batch_mode, root)
    file_processor.process_selected_files()


def clear_treeview(event=None):
    """Clear all items from the treeview."""
    files_tree.delete(*files_tree.get_children())
    FileHandler.update_remove_tags_button()


def clear_output_text(event=None):
    """Clear all text from the output_text widget."""
    output_text.configure(state="normal")
    output_text.delete(1.0, tk.END)
    output_text.configure(state="disabled")


class ToolTip:
    """Creates a tooltip for a given widget."""
    treeview_font = UIConfig.treeview_text()

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Motion>", self.on_motion)
        self.widget.after_id = None
        self.current_item = None

    @staticmethod
    def _should_show_tooltip(event, item, column, bbox, text_width):
        """Determine whether to show the tooltip or not."""
        if not bbox:
            return False
        x1, _, _, _ = bbox
        return item and column == "#1" and x1 < event.x < x1 + text_width

    def _get_item_text_and_width(self, item):
        """Return item text and its width."""
        item_text = self.widget.item(item, "values")
        if item_text and item_text[0]:
            text = item_text[0]
            font = ToolTip.treeview_font
            text_width = self.widget.winfo_toplevel().tk.call(
                "font", "measure", font, text
            )
            return text, text_width
        return None, None

    def on_motion(self, event):
        """Handle the motion event for the tooltip."""
        if isinstance(self.widget, ttk.Treeview):
            item = self.widget.identify_row(
                self.widget.winfo_pointerxy()[1] - self.widget.winfo_rooty()
            )
            column = self.widget.identify_column(
                self.widget.winfo_pointerxy()[0] - self.widget.winfo_rootx()
            )

            text, text_width = self._get_item_text_and_width(item)
            bbox = self.widget.bbox(item, column)

            if self._should_show_tooltip(event, item, column, bbox, text_width):
                if item != self.current_item:
                    self.hide_tooltip(event)
                    self.current_item = item
                    self.schedule_tooltip(event)
            else:
                self.hide_tooltip(event)
                self.current_item = None

    def schedule_tooltip(self, event):
        """Schedule the tooltip to be shown."""
        if self.tooltip_window:
            return

        if self.widget.after_id:
            self.widget.after_cancel(self.widget.after_id)

        self.widget.after_id = self.widget.after(1000, self.show_tooltip)

    def show_tooltip(self):
        """Show the tooltip."""
        if isinstance(self.widget, ttk.Treeview):
            item = self.widget.identify_row(
                self.widget.winfo_pointerxy()[1] - self.widget.winfo_rooty()
            )
            if not item:
                return

            item_text = self.widget.item(item, "values")
            tooltip_text = item_text[-1]  # Display the file path as tooltip text

            bbox = self.widget.bbox(
                item,
                self.widget.identify_column(
                    self.widget.winfo_pointerxy()[0] - self.widget.winfo_rootx()
                ),
            )
            x1, y1, x2, y2 = bbox
            text = item_text[0]
            font = ToolTip.treeview_font
            text_width = self.widget.winfo_toplevel().tk.call(
                "font", "measure", font, text
            )

            x = x1 + text_width + self.widget.winfo_rootx() + 10
            y = y1 + self.widget.winfo_rooty() + 2
        else:
            tooltip_text = self.text

            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 15
            y += self.widget.winfo_rooty() + 40

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window,
            text=tooltip_text,
            relief="flat",
            borderwidth=1,
            font=("Roboto", "10", "normal"),
            background="white",
            fg="black",
            padx=2,
            pady=1,
        )
        label.pack()

    def hide_tooltip(self, event):
        """Hide the tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

        if self.widget.after_id:
            self.widget.after_cancel(self.widget.after_id)
            self.widget.after_id = None


if __name__ == "__main__":
    # UI Window
    root = TkinterDnD.Tk()
    root.attributes("-topmost", True)
    root.update()
    root.attributes("-topmost", False)
    root.title("WavFix")
    frame = tk.Frame(root, bg=UIConfig.bg_color(), padx=20, pady=12)
    frame.grid()

    # Files Window
    custom_treeview_style = UIConfig.create_custom_treeview_style()
    UIConfig.configure_treeview_style(custom_treeview_style, UIConfig)
    files_tree = ttk.Treeview(
        frame,
        columns=("Filename", "Bytes", "Path"),
        height=10,
        show="headings",
        style="Custom.Treeview",
    )
    files_tree.heading("Filename", text="Filename")
    files_tree.column("Filename", width=450)
    files_tree.heading("Bytes", text="Bytes ")
    files_tree.column("Bytes", width=84)
    files_tree.heading("Path", text="Path")  # Hidden column for file path
    files_tree.column("Path", width=0, stretch=tk.NO, minwidth=0)
    files_tree.grid(row=3, column=0, columnspan=2)

    # Instantiate File Handler
    file_handler = FileHandler(
        files_tree, [], FileHandler.update_remove_tags_button, root
    )

    # Drag and Drop
    dnd_handler = DnDHandler(file_handler)
    root.drop_target_register(DND_FILES)
    root.dnd_bind("<<Drop>>", dnd_handler)

    # Output Window
    output_text = CTkTextbox(
        master=frame,
        wrap='word',
        state="disabled",
        cursor="arrow",
        fg_color=UIConfig.window_color(),
        border_spacing=0,
        width=534,
        height=UIConfig.output_window_height(),
        border_width=0,
        corner_radius=UIConfig.window_curves(),
        activate_scrollbars=False,
        font=UIConfig.output_font()
    )
    output_text.configure(text_color=UIConfig.output_text_color())
    output_text.grid(row=4, column=0, columnspan=2, pady=(1, 10))

    # Files Select Button
    files_select_button = CTkButton(
        frame,
        text="Files Select",
        command=lambda: file_handler.select_files(),
        bg_color=UIConfig.bg_color(),
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        corner_radius=UIConfig.button_curves(),
        border_color=UIConfig.accent_color(),
        border_width=2,
        width=UIConfig.button_width(),
    )
    files_select_button.grid(row=5, column=0, columnspan=2, sticky="w", padx=(40, 0))

    # Batch Select Button
    batch_select_button = CTkButton(
        frame,
        text="Batch Select",
        command=lambda: (file_handler.select_folder(), None)[1],
        width=UIConfig.button_width(),
        bg_color=UIConfig.bg_color(),
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        corner_radius=UIConfig.button_curves(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    batch_select_button.grid(row=5, column=0, columnspan=2)

    # Remove Tags Button
    remove_tags_button = CTkButton(
        frame,
        text="Remove Tags",
        command=initiate_export,
        width=UIConfig.button_width(),
        bg_color=UIConfig.bg_color(),
        fg_color=UIConfig.button_color(),
        hover_color=UIConfig.hover_color(),
        text_color=UIConfig.button_text_color(),
        corner_radius=UIConfig.button_curves(),
        border_color=UIConfig.accent_color(),
        border_width=2,
    )
    remove_tags_button.grid(row=5, column=0, columnspan=2, sticky="e", padx=(0, 40))

    FileHandler.update_remove_tags_button()  # Enables/disables remove tags button

    # Color Info Text
    good_bad_label = CTkLabel(
        master=frame,
        text="Green = Good",
        font=("Roboto", 11, "bold"),
        fg_color=UIConfig.bg_color(),
        text_color=UIConfig.green_files_color(),
    )
    good_bad_label.grid(row=2, column=0, sticky=" w", padx=(5, 0), pady=(0, 0))

    bad_label = CTkLabel(
        master=frame,
        text="Red = Bad",
        font=("Roboto", 11, "bold"),
        fg_color=UIConfig.bg_color(),
        text_color=UIConfig.red_files_color(),
    )
    bad_label.grid(row=2, column=0, sticky="w", padx=(97, 0), pady=(0, 0))

    # Bytes Info Text
    bytes_info_label = CTkLabel(
        master=frame,
        text="Should be 01 00",
        font=("Roboto", 11, "bold"),
        fg_color=UIConfig.bg_color(),
        text_color=UIConfig.accent_color(),
    )
    bytes_info_label.grid(row=2, column=1, sticky="e", padx=(0, 5), pady=(0, 0))

    # Author Label
    author_label = CTkLabel(
        master=frame,
        text="By Dreamwalker",
        font=("Roboto", 11, "bold"),
        anchor="w",
        fg_color=UIConfig.bg_color(),
        text_color=UIConfig.accent_color(),
    )
    author_label.grid(row=6, column=0, columnspan=2, sticky="s", pady=(12, 4))

    # Bindings
    files_tree.bind(
        "<Button-1>", clear_treeview
    )
    output_text.bind(
        "<Button-1>", clear_output_text
    )
    author_label.bind(
        "<Button-1>", lambda event: UIConfig.toggle_dark_mode(style=custom_treeview_style),
    )

    # Tooltips
    treeview_tooltip = ToolTip(files_tree, "")
    
    files_select_tooltip = ToolTip(
        files_select_button, "Select files for processing"
    )
    batch_select_tooltip = ToolTip(
        batch_select_button, "Select a folder for batch processing"
    )
    remove_tags_tooltip = ToolTip(
        remove_tags_button, "Choose output path and clean files"
    )

    UIConfig.update_widget_colors(custom_treeview_style)

    root.mainloop()

# WavFix, by Dreamwalker
