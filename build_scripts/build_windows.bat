@echo off

REM Copyright (C) 2023-2026 Auragami
REM
REM This file is part of WavFix.
REM
REM WavFix is free software: you can redistribute it and/or modify
REM it under the terms of the GNU General Public License as published by
REM the Free Software Foundation, either version 3 of the License, or
REM (at your option) any later version.
REM
REM WavFix is distributed in the hope that it will be useful,
REM but WITHOUT ANY WARRANTY; without even the implied warranty of
REM MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
REM GNU General Public License for more details.
REM
REM You should have received a copy of the GNU General Public License
REM along with WavFix.  If not, see <http://www.gnu.org/licenses/>.

REM Parse input arguments
set "USE_CONDA=0"
set "USE_VENV=0"
set "USE_FREEZE=0"
set NEW_VENV_CREATED=0
if not defined RELEASE_PYTHON_VERSION set "RELEASE_PYTHON_VERSION=3.12"
setlocal enabledelayedexpansion

REM Parse arguments
:arg_loop
if "%1" == "" goto arg_loop_end
if "%1" == "-v" (
    set "USE_VENV=1"
    shift & goto arg_loop
)
if "%1" == "-c" (
    set "USE_CONDA=1"
    shift & goto arg_loop
)
if "%1" == "-f" (
    set "USE_FREEZE=1"
    shift & goto arg_loop
)
shift & goto arg_loop
:arg_loop_end


REM Check if any virtual environment is active
if not defined VIRTUAL_ENV if not defined CONDA_PREFIX (
  set NEW_VENV_CREATED=1
  REM Create and activate the virtual environment
  if "!USE_CONDA!" == "1" (
    echo Building Conda environment...
    conda create --yes -n wavfix_env python=!RELEASE_PYTHON_VERSION!
    call activate wavfix_env
    echo Python path: & where python | findstr /I /R /C:"python.exe" /C:"python[0-9]*\.exe"
    FOR /F "tokens=* USEBACKQ" %%F IN (`echo !CONDA_PREFIX!`) DO (SET CONDA_PREFIX=%%F)
    echo Conda environment path: !CONDA_PREFIX!
  ) else (
    echo Building virtual environment...
    py -!RELEASE_PYTHON_VERSION! -m venv venv
    if errorlevel 1 (
        echo Python !RELEASE_PYTHON_VERSION! was not found.
        echo Install Python !RELEASE_PYTHON_VERSION! or build with Conda using -c.
        exit /b 1
    )
    call venv\Scripts\activate
    echo Python path: & where python | findstr /I /R /C:"python.exe" /C:"python[0-9]*\.exe"
    FOR /F "tokens=* USEBACKQ" %%F IN (`echo !VIRTUAL_ENV!`) DO (SET VIRTUAL_ENV=%%F)
    echo Virtual environment path: !VIRTUAL_ENV!
  )
) else (
  echo A virtual environment is already active.
)

REM Announce virtual environment source
if defined VIRTUAL_ENV (
  echo Proceeding using the active virtual environment: !VIRTUAL_ENV!
) else if defined CONDA_PREFIX (
  echo Proceeding using the active Conda environment: !CONDA_PREFIX!
)

python -c "import sys; expected=tuple(map(int, '!RELEASE_PYTHON_VERSION!'.split('.'))); actual=sys.version_info[:len(expected)]; raise SystemExit(0 if actual == expected else 1)"
if errorlevel 1 (
    echo Release artifacts must be built with Python !RELEASE_PYTHON_VERSION!.
    python --version
    exit /b 1
)
echo Release Python version:
python --version

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt


REM Build with the options selected by the user
if "!USE_FREEZE!" == "1" (
    echo Building WavFix with cx_Freeze...
    pip install cx_freeze
    if "!USE_VENV!" == "1" (
        echo Using active virtual environment to source Python standard libraries...
        python src\setup.py -v build_exe
    ) else if "!USE_CONDA!" == "1" (
        echo Using active Conda environment to source Python standard libraries...
        python src\setup.py build_exe
    ) else (
        echo Using system path to source Python standard libraries...
        python src\setup.py build_exe
    )
) else (
    echo Building WavFix with PyInstaller...
    if "!USE_VENV!" == "1" (
        echo Using active virtual environment to source Python standard libraries...
        python -m PyInstaller src/WavFix.spec
    ) else if "!USE_CONDA!" == "1" (
        echo Using active Conda environment to source Python standard libraries...
        python -m PyInstaller src/WavFix.spec
    ) else (
        echo Using system path to source Python standard libraries...
        python -m PyInstaller src/WavFix.spec
    )
)


REM Cleanup
echo Cleaning up...

if !NEW_VENV_CREATED! == 1 (
  if "!USE_CONDA!" == "1" (
      echo Removing Conda environment...
      call conda deactivate
      call conda env remove -n wavfix_env
  ) else (
      echo Removing virtual environment...
      call deactivate
      rmdir /s /q venv
  )
)

if "!USE_FREEZE!" == "1" (
  echo Cleaning up build files...
  mkdir build
  move /y WavFix build\
) else (
    echo Cleaning up build files...
    if exist build rmdir /s /q build
    mkdir build
    if exist dist\WavFix.exe (
        move /y dist\WavFix.exe build\
    ) else (
        echo Expected PyInstaller artifact was not found.
        exit /b 1
    )
    if exist dist rmdir /s /q dist
)

echo Build complete!
if "!USE_FREEZE!" == "1" (
  echo Frozen executable is located in: build/WavFix/WavFix.exe
) else (
  echo Compiled executable is located in: build/WavFix.exe
  )

endlocal

REM WavFix build script, by Auragami
REM v2.0.0
