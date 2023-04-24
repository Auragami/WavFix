#!/bin/bash
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

# Highlight output
IMPORTANT="\033[38;5;207m"
STATUS="\033[0;94m"
WARNING="\033[0;33m"
ERROR="\033[0;31m"
RESET="\033[0m"

# Parse input arguments
USE_CONDA=0
USE_VENV=0
USE_FREEZE=0
NEW_VENV_CREATED=0
while getopts ":vcf" opt; do
  case $opt in
    v)
      USE_VENV=1
      ;;
    c)
      USE_CONDA=1
      ;;
    f)
      USE_FREEZE=1
      ;;
    \?)
      echo -e "${ERROR}Invalid option: -$OPTARG${RESET}" >&2
      exit 1
      ;;
  esac
done


# Check if any virtual environment is active
if [ -z "$VIRTUAL_ENV" ] && [ -z "$CONDA_PREFIX" ]; then
  NEW_VENV_CREATED=1
  # Create and activate a virtual environment
  if [ $USE_CONDA -eq 1 ]; then
    echo -e "${STATUS}Building Conda environment...${RESET}"
    conda create -y -n wavfix_env python=3.11
    eval "$(conda shell.bash hook)"
    conda activate wavfix_env
    echo -e "${WARNING}Python path: $(which python)${RESET}"
    echo -e "${WARNING}Conda environment path: $CONDA_PREFIX${RESET}"
  else
    echo -e "${STATUS}Building virtual environment...${RESET}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${WARNING}Python path: $(which python)${RESET}"
    echo -e "${WARNING}Virtual environment path: $VIRTUAL_ENV${RESET}"
  fi
else
  echo -e "${WARNING}A virtual environment is already active.${RESET}"
fi

# Announce virtual environment source
if [ -n "$VIRTUAL_ENV" ]; then
  echo -e "${IMPORTANT}Proceeding using the active virtual environment: $VIRTUAL_ENV${RESET}"
elif [ -n "$CONDA_PREFIX" ]; then
  echo -e "${IMPORTANT}Proceeding using the active Conda environment: $CONDA_PREFIX${RESET}"
fi


# Install dependencies
echo -e "${STATUS}Installing dependencies...${RESET}"
pip install -r requirements.txt


# Build with the options selected by the user
if [ $USE_FREEZE -eq 1 ]; then
  echo -e "${STATUS}Building WavFix with cx_Freeze...${RESET}"
  pip install cx_freeze
  if [ $USE_VENV -eq 1 ]; then
    echo -e "${WARNING}Using active virtual environment to source Python standard libraries...${RESET}"
    python3 src/setup.py -v bdist_mac
  else
    echo -e "${WARNING}Using system path to source Python standard libraries...${RESET}"
    python3 src/setup.py bdist_mac
  fi
elif [ $USE_VENV -eq 1 ]; then
  echo -e "${STATUS}Building WavFix with PyInstaller...${RESET}"
  echo -e "${WARNING}Using active virtual environment to source Python standard libraries...${RESET}"
  USE_VENV=1 pyinstaller src/WavFix.spec
else
  echo -e "${STATUS}Building WavFix with PyInstaller...${RESET}"
  echo -e "${WARNING}Using system path to source Python standard libraries...${RESET}"
  pyinstaller src/WavFix.spec
fi


# Cleanup
echo -e "${STATUS}Cleaning up...${RESET}"

if [ $NEW_VENV_CREATED -eq 1 ]; then
  if [ $USE_CONDA -eq 1 ]; then
    echo -e "${STATUS}Removing Conda environment...${RESET}"
    conda deactivate
    conda env remove -n wavfix_env
  else
    echo -e "${STATUS}Removing virtual environment...${RESET}"
    rm -rf venv
  fi
fi

if [ $USE_FREEZE -eq 0 ]; then
  echo -e "${STATUS}Cleaning up build files...${RESET}"
  rm -rf build/*
  mv dist/WavFix.app build/
  rm -rf dist
else
  echo -e "${STATUS}Cleaning up build files...${RESET}"
  find build -mindepth 1 -maxdepth 1 ! -name 'WavFix.app' -exec rm -rf {} +
fi

echo -e "${IMPORTANT}Build complete!${RESET}"
echo -e "${IMPORTANT}Compiled app is located in: "build/WavFix.app"${RESET}"
