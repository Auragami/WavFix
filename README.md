# WavFix

<img width="686" alt="lightmode" src="https://user-images.githubusercontent.com/131020999/233953809-b8d1e9a4-cc83-4615-816c-b7d5f8f175e7.png">

By Dreamwalker (C) 2023

## Overview

WavFix is a lightweight application designed to fix the Pioneer DJ Error E-8305, caused by the wFormat flag inserted into some WAV files. The application corrects this error without encoding or changing the audio, and supports batch processing.

## Project Structure

- `build_scripts/`: Contains build scripts to automate compiling the application.
- `src/`: Source code and setup files for the WavFix application.
  - `WavFix.py`: The main source code file for the WavFix application.
  - `Info.plist`: A property list file containing metadata for macOS.
  - `setup.py`: A setup script for building the application using cx_Freeze.
  - `WavFix.spec`: A specification file for building the application using PyInstaller.
- `docs/`: User Guide and images used in documentation.
- `icons/`: Icon files for the application in .icns and .ico formats.

## Table of Contents

- [Features](#features)
- [How to use WavFix](#how-to-use-wavfix)
- [Smart Save System](#smart-save-system)
- [Compiling WavFix](#compiling-wavfix)
  - [Prerequisites](#prerequisites)
  - [Build scripts](#build-scripts)
  - [Setting Up](#setting-up)
  - [Build Instructions](#build-instructions)
  - [Installing WavFix](#installing-wavfix)
  - [Troubleshooting](#troubleshooting)
    - [Conda environments](#conda-environments)
    - [Building with cx_Freeze](#building-with-cx_freeze)
- [Contributing](#contributing)
- [Code of Conduct](#code-of-conduct)
- [Acknowledgements](#acknowledgements)
- [Support](#support)
- [License](#license)

## Features

- Selectively removes wFormatTags from WAV files
- Support for batch processing
- Preservation of the original file structure
- Smart Save system to prevent unintentional data loss
- Supports common album file types, including audio, images, and documents

## How to use WavFix

1. Launch the WavFix application.
2. Drag files or a folder into WavFix.
3. Once the files are loaded into the application, click on the "Remove Tags" button.
4. Select an output directory, and the modified files will be saved there.

For a more detailed guide on using the application, refer to the [WavFix User Guide](docs/WavFix_User_Guide.pdf).

## Smart Save System

WavFix's Smart Save system simplifies the file-saving process and minimizes the risk of accidentally overwriting existing files. When exporting, WavFix looks in the output destination for files that are the same type and name as the input files. The user can choose to overwrite the files or save the modified files in a new folder, appending "_clean" to the folder name.

## Compiling WavFix

*The rest of this README covers the necessary steps to build WavFix from source code.*
For more information about WavFix, please see the [WavFix User Guide](docs/WavFix_User_Guide.pdf).

### Prerequisites

**Note:** Before you begin, consider using Conda or another virtual environment manager, as described in [Conda environments](#conda-environments).
If you are using Conda, you can skip installing Python if you do not have it already.

Install Python 3.8 or later from the official website: <https://www.python.org/downloads/>

### Build Scripts

This repository includes a shellcode (.sh) and batch (.bat) build script for MacOS and Windows respectively. These files have been included to streamline the build process by automating the steps detailed in the following sections.

The build scripts have been programmed to accept arguments that allow any variation of the build process to be selected.
The arguments can simply be added to the end of the command that runs the build script.

- `-v` - Sources the Python standard libraries from your virtual environment instead of the system libraries.
- `-c` - Builds the virtual environment using Conda instead of Python (should be accompanied by the `-v` argument).
- `-f` - Builds the application using cx_Freeze instead of PyInstaller (not recommended).

*If you execute the build script with a virtual environment active, that environment will be used instead of creating a new one.*

To understand these arguments more thoroughly, please read the information in [Build Instructions](#build-instructions), [Conda Environments](#conda-environments), and [Building with cx-Freeze](#building-with-cx_freeze).

To use the build scripts:

Open a Terminal or Command Prompt and navigate to the WavFix root directory where this README is located.
This can be done by entering 'cd ' (with the space) into your Terminal or Command Prompt, and then dragging the WavFix directory into the Terminal or Command Prompt window. Press enter.

**MacOS:**

To build the project on MacOS, you may first need to grant execute permissions to the script:

    chmod +x build_scripts/build_mac.sh

Then, execute the script:

    ./build_scripts/build_mac.sh

**Windows:**

To build the project on Windows, execute the `build_windows.bat` script located in the `build_scripts` folder:

    build_scripts\build_windows.bat

These scripts perform the following actions:

1. Creates a virtual environment if one is not active
2. Activates the new virtual environment (or Conda environment) if one was created
3. Installs dependencies from the `requirements.txt` file
4. Builds the project using the `src/WavFix.spec` or `src/setup.py` file
5. The virtual environment or Conda environment created by the script is deleted
6. Unnecessary files created during the build are deleted

After the build script finishes and successfully compiles the application, it can be found in `build` folder.

More information and a download link for Conda can be found in the [Conda environments](#conda-environments) section.

### Setting Up

If you want to compile the application by hand, instead of using the build scripts, you can do so following the steps outlined in the following sections. The commands detailed in these sections are what is executed by the build scripts.

#### Create a virtual environment

Open a Terminal or Command Prompt, and navigate to the WavFix root directory where this README is located.

(For instructions using Conda, go to the 'Conda environments' section)

**MacOS:**

In Terminal run:

    python3 -m venv venv

Activate the virtual environment:

    source venv/bin/activate

**Windows:**

In Command Prompt run:

    python -m venv venv

Activate the virtual environment:

    venv\Scripts\activate

You should now see (venv) at the beginning of your terminal or command prompt, indicating that the virtual environment is active.

#### Install dependencies

With your virtual environment active, navigate to the WavFix root directory where this README is located.

Install the required dependencies using this command:

    pip install -r requirements.txt

Your virtual environment is now set up and the dependencies are installed.

### Build Instructions

WavFix is most optimally built with PyInstaller. PyInstaller writes all of the dependencies to binary, resulting in a much smaller executable. Also, the resulting app will play nicer with Apple's Gatekeeper security feature. However, if for whatever reason you cannot use PyInstaller, instructions for building the app using cx_Freeze are in the 'Troubleshooting' section below.

The 'WavFix.spec' script contains an optional argument that can be added to the Command Prompt/Terminal command. This argument determines if the setup script will package standard library dependencies from your system libraries or the active virtual environment.
The argument is `USE_VENV=1`, which can be added to the beginning of the command.

*For builds using the method described in 'Create virtual environment' above, you must NOT include this optional argument.*

For builds using Conda, or other methods creating a virtual environment with the standard library dependencies, you should include this optional argument.

#### Building with PyInstaller (recommended)

- Activate your virtual environment if it is not active from previous steps.
- Navigate to the WavFix folder where this README is located.

For system standard libraries:

    pyinstaller src/WavFix.spec

For venv sourced standard libraries on MacOS:

    USE_VENV=1 pyinstaller src/WavFix.spec

For venv sourced standard libraries on Windows:

    set "USE_VENV=1" && pyinstaller src/WavFix.spec

- Wait for the packager to finish.

**Note:** The solution for adding the icon on Windows is still needed.

### Installing WavFix

**Mac Installation**
After completing the build instructions, the finished .app is located here: WavFix/dist/*WavFix.app* <---
The bundled app does not have dependencies, and so can be placed anywhere.
You can delete the rest of the build folder, or the entire WavFix repository.

**PC Installation**
After completing the build instructions, the finished .exe is located here: WavFix/dist/*WavFix.exe* <---
The bundled executeable does not have dependencies, and so can be placed anywhere.
You can delete the rest of the build folder, or the entire WavFix repository.

If you created the virtual environment with Conda, make sure to delete that as well; if you no longer need it.

### Troubleshooting

#### Conda environments

If you have issues with the executable, I recommend using Anaconda3 to build your virtual environment for bundling the app. You can use whatever you prefer for creating a virtual environment with the standard libraries. Conda is what I have used and had good results with. I am completely unaffiliated with them.
Building a virtual environment like this is more reliable in terms of bundling the standard library dependencies.
Conda may reduce, or increase, the file size of the final application by a small amount.

**Setting up a conda environment:**

Install Anaconda from the official website: <https://www.anaconda.com/products/distribution>
Open a terminal or command prompt, and navigate to the WavFix root directory, where this README is located.
Create a conda environment by running the following command:

    conda create -n wavfix_env python=3.11

**Activate the conda environment:**

For MacOS, in terminal run:

    conda activate wavfix_env

For Windows, in command prompt run:

    activate wavfix_env

You should now see `(wavfix_env)` at the beginning of your terminal or command prompt, indicating that the conda environment is active.

The instructions provided for building the app remain the same, except you will use the applicable argument to use your active virtual environment instead of the system libraries.

Continue to 'Install dependencies' before building the app.

#### Building with cx_Freeze

Bundling the app with cx_Freeze on MacOS will results in a much larger application that will have issues with Gatekeeper. On Windows, it will result in file with frozen dependencies and an executable you will need to make a shortcut to; instead of a single file executable. For those reasons it is not recommended. PyInstaller writes the dependencies along with the source code to binary, which produces a much more desireable result. However, if for some reason you cannot use PyInstaller, cx_Freeze is the best option for bundling WavFix along with its necessary dependancy files.
To use the resulting application on MacOS systems, you will likely need to disable Gatekeeper.

I recommend that you use the build scripts provided for building with cx_Freeze. Please see [Build Scripts](#build-scripts).

The 'setup.py' script contains an optional argument that can be added to the Command Prompt/Terminal command. This argument determines if the setup script will package standard library dependencies from your system libraries, or the active virtual environment.

The arguments are: '-v' or '--use-venv' and can be added after specifying the setup script, as follows:

For MacOS:

    python3 src/setup.py -v bdist_mac

For PC:

    python src\setup.py -v build_exe

*For builds using the method described in 'Create virtual environment' above, you must NOT include this optional argument.*

For builds using Conda, or other methods of creating the virtual environment with the standard library dependencies, you should include this optional argument.

##### cx_Freeze instructions

1. Activate your virtual environment, if it is not active from previous steps.
2. Navigate to the WavFix folder where this README is located.
3. In Terminal or Command Prompt, run: `pip install cx_Freeze`

**For Mac:**

In Terminal run:

    python3 src/setup.py bdist_mac

Add the `-v` argument if using conda.
Wait for the packager to finish.

**For PC:**

In Command Prompt run:

    python setup\setup.py build_exe

Add the `-v` argument if using conda.
Wait for the packager to finish.

If for some reason you are having trouble with the bundled file, you can run:

***MacOS***

    python3 src/setup.py build

***Windows***

    python src\setup.py build

This will create a unix executable.

## Contributing

We encourage and welcome contributions to WavFix. If you're interested in contributing, please read our [CONTRIBUTING](CONTRIBUTING.md) guidelines and [Code of Conduct](CODE_OF_CONDUCT.md).

## Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to abide by its terms.

## Acknowledgements

I would like to express my gratitude to the following individuals and organizations for their contributions, support, and assistance in the development of WavFix:

- OpenAI: For building ChatGPT4.
- Ryan Taylor: For help with testing the setup files and application bundling.
- My Mother:  For always supporting me and encouraging me to pursue my interests.

I sincerely appreciate the efforts of everyone involved in making WavFix a better tool for the community. If you have contributed to the project and would like to be acknowledged here, please let me know by contacting me through one of the channels mentioned in the [Support](#support) section.

## Support

If you encounter any issues while using WavFix or have any questions regarding the project, please feel free to:

1. Check the [User Guide and Documentation](docs/WavFix_User_Guide.pdf) for detailed information and usage instructions.
2. Submit a [GitHub issue](https://github.com/Dreamwalkertunes/WavFix/issues) with a description of your problem or question.
3. Email me at [wavfix.dev@gmail.com](mailto:wavfix.dev@gmail.com).
4. Reach out to me on Twitter: [@Dreamwalkertune](https://twitter.com/Dreamwalkertune).

I'll do my best to help you out and address any issues you may encounter.

### Reporting Bugs

If you've found a bug in the project, please [submit an issue on GitHub](https://github.com/Dreamwalkertunes/WavFix/issues) with a detailed description of the problem and steps to reproduce it. Make sure to search for existing issues to avoid duplicates.

## License

WavFix is released under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
