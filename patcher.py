import os
import time
import xmltodict
import questionary
from rich.console import Console
from pathlib import Path
import shutil
import subprocess

def run_command(cmd, check=True):
    """Run shell command, raise on error."""
    print(f"Running command: {cmd}")
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr)
        raise RuntimeError(f"Command failed: {cmd}")
    print(proc.stdout)
    return proc.stdout


console = Console()
sd_root = Path(__file__).parent / "sd_files"
riivolution_path = sd_root / "riivolution"

# find XML
if not riivolution_path.exists():
    console.print('[bold red]"sd_files/riivolution" does not exist. Ending script.[/bold red]')
    exit(1)

xml_files = [f for f in os.listdir(riivolution_path) if f.endswith(".xml")]

if not xml_files:
    console.print('[bold red]No XML files found in "sd_files/riivolution". Ending script.[/bold red]')
    exit(1)

# select XML
xml_choice = questionary.select(
    "Select a Riivolution XML file:",
    choices=xml_files
).ask()

selected_xml_path = riivolution_path / xml_choice
xml_root_folder = selected_xml_path.stem

# parse XML
with open(selected_xml_path, "r", encoding="utf-8") as f:
    xml_data = xmltodict.parse(f.read())

# Extract patches
patches = xml_data["wiidisc"]["patch"]
if not isinstance(patches, list):
    patches = [patches]

# ask which patches to apply
patch_ids = [patch["@id"] for patch in patches]

selected_patch_ids = []
for patch_id in patch_ids:
    answer = questionary.select(
        f'Apply patch "{patch_id}"?',
        choices=["Yes", "No"]
    ).ask()
    if answer == "Yes":
        selected_patch_ids.append(patch_id)

filtered_patches = [patch for patch in patches if patch["@id"] in selected_patch_ids]

console.print("\n[bold green]Selected patches:[/bold green]")
for patch in filtered_patches:
    console.print(f"- {patch['@id']}")


folders = []
files = []
memory = []
for patch in filtered_patches:
    patch_folders = patch.get("folder", [])
    if not isinstance(patch_folders, list):
        patch_folders = [patch_folders]
    for f in patch_folders:
        if f and f.get("@disc") and f.get("@external"):
            # external_path = f["@external"]
            # if not external_path.startswith(xml_root_folder):
            #     f["@external"] = f"{xml_root_folder}/{external_path}"
            folders.append(f)

    patch_files = patch.get("file", [])
    if not isinstance(patch_files, list):
        patch_files = [patch_files]
    for fi in patch_files:
        if fi and fi.get("@disc") and fi.get("@external"):
            # external_path = fi["@external"]
            # if not external_path.startswith(xml_root_folder):
            #     fi["@external"] = f"{xml_root_folder}/{external_path}"
            files.append(fi)

    mems = patch.get("memory", [])
    if not isinstance(mems, list):
        mems = [mems]
    for m in mems:
        if m and m.get("@offset") and (m.get("@value") or m.get("@valuefile")):
            memory.append(m)

if not folders and not files and not memory:
    console.print("[red]No patches with folders, files or memory found. Ending script.[/red]")
    exit(1)

answer = questionary.select(
    "Continue with patch?",
    choices=["Yes", "No"]
).ask()

if answer != "Yes":
    console.print("[red]Ending script.[/red]")
    exit(1)


# Choose and extract disc image

source_path = Path("disc_image")
disc_files = list(source_path.glob("*.wbfs")) + list(source_path.glob("*.iso"))
if not disc_files:
    print(f"No .wbfs or .iso files found in '{source_path}'")
    exit(1)

if len(disc_files) > 1:
    choices = [f.name for f in disc_files]
    selected_name = questionary.select(
        "Multiple disc images found. Select one to use:",
        choices=choices
    ).ask()
    if not selected_name:
        print("No selection made. Exiting.")
        exit(1)
    selected_file = next(f for f in disc_files if f.name == selected_name)
else:
    selected_file = disc_files[0]
    print(f"Selected disc image: {selected_file}")


dest_path = Path("tmp")
if dest_path.exists():
    shutil.rmtree(dest_path)

cmd_extract = f'wit EXTRACT "{str(selected_file)}" {dest_path}'
print('\033[33mRunning "wit EXTRACT"... (This may take a while)\033[0m')  # yellow text
run_command(cmd_extract)


print('\033[33mPatching Files...\033[0m')

# Copy folders
for folder in folders:
    src = sd_root/ xml_root_folder / folder['@external']
    dest = dest_path / 'files' / folder['@disc']
    if src.exists():
        dest.mkdir(parents=True, exist_ok=True)
        print(f'Copying folder {src} -> {dest}')
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        time.sleep(0.01)
    else:
        print(f'\033[31m"{src}" does not exist. Skipping.\033[0m')

# Copy files
for file in files:
    src = sd_root/ xml_root_folder / file['@external']
    if not src.exists():
        print(f'\033[31m"{src}" does not exist. Skipping.\033[0m')
        continue

    adjusted_path = None
    for root, dirs, filenames in os.walk(dest_path):
        if file['@disc'] in root:
            adjusted_path = Path(root)
            break

    if not adjusted_path:
        adjusted_path = dest_path / 'files' / file['@disc']
        adjusted_path.parent.mkdir(parents=True, exist_ok=True)

    print(f'Copying file {src} -> {adjusted_path}')
    shutil.copy2(src, adjusted_path)
    time.sleep(0.01)


patched_dir = Path("patched_disc_image")
patched_dir.mkdir(parents=True, exist_ok=True)

cmd_copy = f'wit COPY {dest_path} {patched_dir}/game.wbfs'
print('\033[33mRunning "wit COPY"... (This may take a while)\033[0m')
run_command(cmd_copy)

# Run wit VERIFY
cmd_verify = f'wit VERIFY {patched_dir}/game.wbfs'
print('\033[33mRunning "wit VERIFY"... (This may take a while)\033[0m')
run_command(cmd_verify)

# Ask if remove tmp folder
remove_tmp = questionary.select(
    "Remove tmp folder?",
    choices=["Yes", "No"]
).ask()

if remove_tmp == "Yes":
    print('\033[33mRemoving tmp files...\033[0m')
    shutil.rmtree(dest_path)
else:
    print('\033[31mKeeping tmp files.\033[0m')

print('\033[32mDone! Patched file is located at "' + str(patched_dir) + '/game.wbfs". Ending Script.\033[0m')