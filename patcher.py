import os
import xmltodict
import questionary
from rich.console import Console
from pathlib import Path
import shutil


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