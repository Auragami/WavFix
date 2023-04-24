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


# Check if the venv flag is set to 1 or 0
use_venv = os.environ.get('USE_VENV', '0') == '1'

# Get Tcl and Tk libraries paths
tcl_library, tk_library = get_library_paths(use_venv)

# Get customtkinter and tkinterdnd2 library paths
customtkinter_path, tkinterdnd2_path = get_packages_paths()


# Configure PyInstaller
block_cipher = None

a = Analysis(
    ['./WavFix.py'],
    pathex=['.'],
    binaries=[],
    datas=[('../icons', 'icons'),
           (customtkinter_path, 'customtkinter'),
           (tkinterdnd2_path, 'tkinterdnd2'),
           (tcl_library, 'tcl8.6'),
           (tk_library, 'tk8.6')],
    hookspath=[],
    runtime_hooks=[],
    hiddenimports=['customtkinter'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WavFix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    icon='../icons/icon.ico'
)

# Plist information
info_plist = {
    'CFBundleName': 'WavFix',
    'CFBundleDisplayName': 'WavFix',
    'CFBundleGetInfoString': 'WavFix by Dreamwalker',
    'CFBundleVersion': '1.0.0',
    'CFBundleShortVersionString': '1.0',
    'CFBundleIdentifier': 'com.dreamwalker.WavFix',
    'NSHumanReadableCopyright': 'Copyright (C) 2023 Dreamwalker',
    'CFBundleIconFile': 'icon.icns',
}

# Bundle information
app = BUNDLE(
    exe,
    name='WavFix.app',
    icon='../icons/icon.icns',
    bundle_identifier=None,
    info_plist=info_plist
)
