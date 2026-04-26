import os
from pathlib import Path
import shutil
import platform

# Directory where this script lives
script_dir = os.path.dirname(os.path.abspath(__file__))

# Build path to your file
csv_filepath = os.path.join(script_dir, "timestamps.csv")

script_filepath = "BeatFrameScript.py"

with open(script_filepath, "r") as f:
    lines = f.readlines()

# change the filepath inside the script to be the user's specific filepath
# to the csv file
for i, line in enumerate(lines):
    if line.strip().startswith("CSV_FILEPATH ="):
        lines[i] = "CSV_FILEPATH = \"" + csv_filepath + "\"\n"   # new line

with open(script_filepath, "w") as f:
    f.writelines(lines)

# find davinci resolve filepath of the user
import os
from pathlib import Path
import platform

def get_resolve_scripts_path():
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility")
    elif system == "Windows":
        return Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility")
    elif system == "Linux":
        return Path("/opt/resolve/Fusion/Scripts/Utility")
    else:
        raise Exception("Unsupported OS")

def install_script(source_file):
    dest_dir = get_resolve_scripts_path()
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / Path(source_file).name
    shutil.copy2(source_file, dest_file)

    print(f"BeatFrameScript.py installed to: {dest_file}")

# install script to davinci resolve of user
install_script("BeatFrameScript.py")
