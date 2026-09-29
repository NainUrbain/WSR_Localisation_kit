"""WSR_KR installer shared by the developer and player patch packages."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from patcher_core import apply_entry, load_manifest, sha256, verify_entry

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
PATCHES = load_manifest(ROOT / "patch_manifest.json")
PAYLOAD = json.loads((ROOT / "payload_manifest.json").read_text(encoding="utf-8"))
MODE = PATCHES["mode"]
BACKUP_NAME = f"wsr-kr-{MODE}-backup"
INSTALL_STATE_NAME = "installed_patch.json"
DEBUG_CONFIG = "js/locale/wsr-kr-debug-config.json"


def validate_app(value: str | os.PathLike[str]) -> Path:
    path = Path(value).expanduser().resolve()
    if (path / "resources/app/js/api.js").is_file():
        path = path / "resources/app"
    if not (path / "js/api.js").is_file() or not (path / "js/locale/localeManager.js").is_file():
        raise RuntimeError("Select the Wall Street Raider resources/app folder.")
    return path


def find_app() -> Path:
    candidates: list[Path] = []
    for drive in "CDEFGHIJ":
        for steam in ("Program Files (x86)/Steam", "Steam", "SteamLibrary"):
            app = Path(f"{drive}:/") / steam / "steamapps/common/Wall Street Raider/resources/app"
            if (app / "js/api.js").is_file():
                candidates.append(app)
    if len(candidates) == 1:
        print(f"Game path: {candidates[0]}")
        return candidates[0]
    return validate_app(input("Wall Street Raider installation folder or resources/app path: ").strip().strip('"'))


def find_steam_app_dir() -> str | None:
    """Non-interactive Steam lookup used by the developer pipeline."""
    for drive in "CDEFGHIJ":
        for steam in ("Program Files (x86)/Steam", "Steam", "SteamLibrary"):
            app = Path(f"{drive}:/") / steam / "steamapps/common/Wall Street Raider/resources/app"
            if (app / "js/api.js").is_file():
                return str(app)
    return None


def verify_package() -> None:
    for rel, expected in PAYLOAD.items():
        source = ROOT / "game_files" / "js" / rel
        if not source.is_file() or sha256(source.read_bytes()) != expected:
            raise RuntimeError(f"Installer payload verification failed: {rel}")


def backup_targets(app: Path) -> tuple[Path, dict[str, bool]]:
    backup = app / BACKUP_NAME
    backup.mkdir(exist_ok=True)
    index_path = backup / "original_files.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    targets = [entry["path"] for entry in PATCHES["files"]]
    originals = {entry["path"]: entry["original_sha256"] for entry in PATCHES["files"]}
    targets += ["js/" + rel for rel in PAYLOAD]
    if MODE == "developer":
        targets.append(DEBUG_CONFIG)
    for rel in targets:
        source = app / rel
        if rel in index:
            # A supported clean game update starts a new original version.
            # Do not later restore a backup from before that update.
            if rel in originals and source.is_file() and sha256(source.read_bytes()) == originals[rel]:
                dest = backup / rel
                if not dest.is_file() or sha256(dest.read_bytes()) != originals[rel]:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    index[rel] = True
            continue
        index[rel] = source.is_file()
        if source.is_file():
            dest = backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return backup, index


def prepare_patch_targets(app: Path, backup: Path) -> None:
    """Restore files from the last recorded WSR_KR install before upgrading.

    A clean backup alone is not enough evidence: Steam may have updated the
    game since it was created.  Only trust the backup when the current file
    hash exactly matches the hash recorded after our previous successful
    install.  Unknown modifications still fail closed.
    """
    state_path = backup / INSTALL_STATE_NAME
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    previous = state.get("files", {}) if state.get("format") == 1 else {}
    restore: list[tuple[Path, Path, str]] = []
    for entry in PATCHES["files"]:
        rel = entry["path"]
        target = app / rel
        if not target.is_file():
            raise RuntimeError(f"Missing game file: {rel}")
        digest = sha256(target.read_bytes())
        if digest in {entry["original_sha256"], entry["patched_sha256"]}:
            continue
        source = backup / rel
        if previous.get(rel) == digest and source.is_file() and sha256(source.read_bytes()) == entry["original_sha256"]:
            restore.append((target, source, rel))
            continue
        raise RuntimeError(
            f"Unsupported game version or modified file: {rel}\n"
            f"Current SHA256: {digest}\nRun Steam's file-integrity verification and try again."
        )
    for target, source, rel in restore:
        shutil.copy2(source, target)
        print(f"  {rel}: previous-patch-restored")


def remove_stale_payload(app: Path, index: dict[str, bool]) -> None:
    """Delete files an earlier install added that this package no longer ships."""
    current = {"js/" + rel for rel in PAYLOAD} | {entry["path"] for entry in PATCHES["files"]}
    if MODE == "developer":
        current.add(DEBUG_CONFIG)
    for rel, existed in index.items():
        target = app / rel
        if not existed and rel not in current and target.is_file():
            target.unlink()
            print(f"  {rel}: removed (no longer shipped)")


def save_install_state(backup: Path) -> None:
    state = {
        "format": 1,
        "mode": MODE,
        "files": {entry["path"]: entry["patched_sha256"] for entry in PATCHES["files"]},
        "originals": {entry["path"]: entry["original_sha256"] for entry in PATCHES["files"]},
    }
    target = backup / INSTALL_STATE_NAME
    temp = backup / (INSTALL_STATE_NAME + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)


def install(app: Path) -> None:
    verify_package()
    prepare_patch_targets(app, app / BACKUP_NAME)
    backup, index = backup_targets(app)
    for entry in PATCHES["files"]:
        print(f"  {entry['path']}: {apply_entry(app, entry)}")
    for rel in PAYLOAD:
        source = ROOT / "game_files" / "js" / rel
        dest = app / "js" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    if MODE == "developer":
        debug_dir = ROOT / "debug_output"
        debug_dir.mkdir(exist_ok=True)
        config = app / DEBUG_CONFIG
        config.write_text(json.dumps({"debugDir": str(debug_dir)}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    remove_stale_payload(app, index)
    status(app, strict=True)
    save_install_state(backup)
    print(f"{MODE} build installed. Restart the game.")


def status(app: Path, strict: bool = False) -> bool:
    bad = [entry["path"] for entry in PATCHES["files"] if not verify_entry(app, entry)]
    bad += ["js/" + rel for rel, digest in PAYLOAD.items()
            if not (app / "js" / rel).is_file() or sha256((app / "js" / rel).read_bytes()) != digest]
    if bad:
        print("Patch status: mismatch - " + ", ".join(bad))
        if strict:
            raise RuntimeError("Post-installation verification failed.")
        return False
    print(f"Patch status: OK ({len(PATCHES['files'])} game-file deltas + {len(PAYLOAD)} WSR localization files)")
    return True


def uninstall(app: Path) -> None:
    backup = app / BACKUP_NAME
    index_path = backup / "original_files.json"
    if not index_path.is_file():
        raise RuntimeError("No backup created by this installer was found.")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    # Check the entire restore set before changing anything. In particular,
    # uninstall must not overwrite an unrecognized Steam update or user edit.
    state_path = backup / INSTALL_STATE_NAME
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    expected = state.get("files", {})
    for entry in PATCHES["files"]:
        rel = entry["path"]
        current, original = app / rel, backup / rel
        original_hash = state.get("originals", {}).get(rel, entry["original_sha256"])
        if not original.is_file() or sha256(original.read_bytes()) != original_hash:
            raise RuntimeError(f"Original backup verification failed: {rel}")
        allowed = {expected.get(rel, entry["patched_sha256"])}
        if original.is_file():
            allowed.add(sha256(original.read_bytes()))
        if not current.is_file() or sha256(current.read_bytes()) not in allowed:
            raise RuntimeError(f"Refusing to overwrite changed game file during uninstall: {rel}")
    for rel, existed in index.items():
        if existed and not (backup / rel).is_file():
            raise RuntimeError(f"Missing backup file: {rel}")
    for rel, existed in index.items():
        dest = app / rel
        if existed:
            source = backup / rel
            if not source.is_file():
                raise RuntimeError(f"Missing backup file: {rel}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        elif dest.is_file():
            dest.unlink()
    state_path = backup / INSTALL_STATE_NAME
    if state_path.is_file():
        state_path.unlink()
    print("Patch removed and pre-installation files restored.")


def main() -> int:
    interactive = len(sys.argv) == 1
    try:
        if interactive:
            action, app = "install", find_app()
        else:
            if len(sys.argv) != 3 or sys.argv[1] not in {"install", "status", "uninstall"}:
                raise RuntimeError('Usage: install_patch.py install|status|uninstall "resources/app path"')
            action, app = sys.argv[1], validate_app(sys.argv[2])
        result = {"install": install, "status": status, "uninstall": uninstall}[action](app)
        if action == "status" and result is False:
            return 1
    except Exception as exc:
        print(f"[Error] {exc}")
        if interactive:
            input("Press Enter to exit.")
        return 1
    if interactive:
        input("Press Enter to exit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
