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
import sys
from cx_Freeze import Executable, setup


def get_library_paths(use_venv):
    """Get the path to the Tcl and Tk libraries."""
    venv_path = sys.prefix
    tcl_library = None
    tk_library = None

    if use_venv:
        # Find the Tcl and Tk library paths in the virtual environment
        for root, dirs, _ in os.walk(venv_path):
            if tcl_library is None and "tcl8.6" in dirs:
                tcl_library = os.path.join(root, "tcl8.6")
            if tk_library is None and "tk8.6" in dirs:
                tk_library = os.path.join(root, "tk8.6")
            if tcl_library and tk_library:
                break
    else:
        # Find the Tcl and Tk library paths in the base environment
        for root, dirs, _ in os.walk(sys.base_prefix):
            if tcl_library is None and "tcl8.6" in dirs:
                tcl_library = os.path.join(root, "tcl8.6")
            if tk_library is None and "tk8.6" in dirs:
                tk_library = os.path.join(root, "tk8.6")
            if tcl_library and tk_library:
                break

    if tcl_library is None or tk_library is None:
        raise FileNotFoundError("Tcl or Tk library not found")

    return tcl_library, tk_library


def get_packages_paths():
    """Get the path to the customtkinter and tkinterdnd2 libraries."""
    venv_path = sys.prefix
    customtkinter_path = None
    tkinterdnd2_path = None

    # Find the customtkinter and tkinterdnd2 library paths
    for root, dirs, _ in os.walk(venv_path):
        if customtkinter_path is None and "customtkinter" in dirs:
            customtkinter_path = os.path.join(root, "customtkinter")
        if tkinterdnd2_path is None and "tkinterdnd2" in dirs:
            tkinterdnd2_path = os.path.join(root, "tkinterdnd2")
        if customtkinter_path and tkinterdnd2_path:
            break

    if customtkinter_path is None or tkinterdnd2_path is None:
        raise FileNotFoundError("customtkinter or tkinterdnd2 library not found")

    return customtkinter_path, tkinterdnd2_path


# Check if the '-v' or '--use-venv' flag is present in the command line arguments
use_venv = '-v' in sys.argv or '--use-venv' in sys.argv
sys.argv = [arg for arg in sys.argv if arg not in ['-v', '--use-venv']]

# Get Tcl and Tk libraries paths
tcl_library, tk_library = get_library_paths(use_venv)
os.environ["TCL_LIBRARY"] = tcl_library
os.environ["TK_LIBRARY"] = tk_library

# Get customtkinter and tkinterdnd2 library paths
customtkinter_path, tkinterdnd2_path = get_packages_paths()

# Configure cx_Freeze
if sys.platform == "win32":
    base = "Win32GUI"
    lib_dylib_ext = ".dll"
    lib_dylib_dest = ""
elif sys.platform == "win64":
    base = "Win64GUI"
    lib_dylib_ext = ".dll"
    lib_dylib_dest = ""
elif sys.platform == "darwin":
    base = "Console"
    lib_dylib_ext = ".dylib"
    lib_dylib_dest = "lib"
else:
    raise Exception("Unsupported platform")

build_options = {
    "include_files": [
        (tcl_library, "tcl8.6"),
        (tk_library, "tk8.6"),
        (customtkinter_path, "customtkinter"),
        (tkinterdnd2_path, "tkinterdnd2"),
    ],
    "includes": ["tkinter", "tkinter.ttk", "customtkinter", "tkinterdnd2"],
    "packages": ["os", "shutil", "tempfile", "pathlib"],
    "excludes": ["tkinter.test"],
    "optimize": 2,
    "build_exe": "WavFix",
}

mac_options = {
    "bundle_name": "WavFix",
    "iconfile": "icons/icon.icns",
    "custom_info_plist": "src/Info.plist",
}

setup(
    name="WavFix",
    version="1.1",
    description="WavFix Application",
    options={"build_exe": build_options, "bdist_mac": mac_options},
    executables=[
        Executable("src/WavFix.py", base=base, icon="icons/icon.ico")
    ],
)

# WavFix cx_Freeze setup file, by Dreamwalker
# v1.1.0
