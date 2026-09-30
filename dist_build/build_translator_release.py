"""Stage the editable translator kit and its installer payload."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

source = Path(args.source).resolve()
output = Path(args.output).resolve()
game_files = output / "game_files" / "js"
if output == source or source.is_relative_to(output) or output.is_relative_to(source):
    raise SystemExit("translator output must be outside the source kit")
# Every registered locale must have current data in a freshly downloaded kit.
profiles = json.loads((source / "locale_profiles.json").read_text(encoding="utf-8"))
for locale in profiles:
    subprocess.run([sys.executable, str(source / "pipeline.py"), "build", "--locale", locale], check=True)
if output.exists():
    shutil.rmtree(output)
game_files.mkdir(parents=True)

source_manifest = json.loads((source / "payload_manifest.json").read_text(encoding="utf-8"))
for rel in source_manifest:
    dest = game_files / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "game_files" / "js" / rel, dest)

patches = json.loads((source / "patch_manifest.json").read_text(encoding="utf-8"))
patches["mode"] = "translator"
(output / "patch_manifest.json").write_text(
    json.dumps(patches, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

manifest = {
    rel: hashlib.sha256((game_files / rel).read_bytes()).hexdigest()
    for rel in source_manifest
}
(output / "payload_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

assert not any("uploader" in rel.lower() for rel in manifest)

for dirname in ("source_data", "reference_data", "locales", "pipeline_tools", "tests"):
    src = source / dirname
    if src.is_dir():
        shutil.copytree(
            src,
            output / dirname,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

for filename in (
    "pipeline.py",
    "install_patch.py",
    "patcher_core.py",
    "key_migrations.csv",
    "key_overrides.json",
    "outlook_combinations.csv",
    "locale_profiles.json",
    "key_structure.json",
    "TOKEN_REFERENCE.md",
    "MULTILINGUAL.md",
):
    src = source / filename
    if src.is_file():
        shutil.copy2(src, output / filename)

for filename in ("LICENSE", "LICENSE-DATA.md"):
    shutil.copy2(Path(__file__).resolve().parents[1] / filename, output / filename)

developer_readme = source / "DEVELOPER_BUILD.md"
if developer_readme.is_file():
    shutil.copy2(developer_readme, output / "README.md")

# The editable kit can produce its own Workshop release without downloading
# another repository. These files use the same builder as the maintainer.
release_tools = output / "release_tools"
release_tools.mkdir()
for filename in ("build_user_release.py", "build_workshop_release.py", "install_patch_dist.py",
                 "patcher_core.py", "patch_manifest.json", "WORKSHOP.md",
                 "workshop-description.ko.txt", "create_workshop_preview.ps1"):
    shutil.copy2(Path(__file__).parent / filename, release_tools / filename)
shutil.copy2(Path(__file__).parent / "build_player_from_kit.bat", output / "build_player.bat")

csv_count = sum(1 for _ in (output / "locales").glob("*/*.csv"))
assert csv_count > 0, "Translator kit must contain editable translation CSV files"
print(
    f"STAGED translator kit: {len(manifest)} runtime files, "
    f"{csv_count} translation CSV files, debug overlay enabled"
)
