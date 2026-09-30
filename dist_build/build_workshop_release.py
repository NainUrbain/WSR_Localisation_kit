"""Build a resources/app-shaped Workshop overlay without changing the game.

Generated game-derived files stay in ignored dist/, never in source control.
"""
from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile

from patcher_core import apply_entry, load_manifest, sha256

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
SOURCE = ROOT if (ROOT / "locale_profiles.json").is_file() else ROOT / "wsr_package_build"


def find_game():
    candidates = []
    for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for library in ("SteamLibrary", "Steam", "Program Files (x86)/Steam"):
            app = Path(f"{drive}:/") / library / "steamapps/common/Wall Street Raider/resources/app"
            if (app / "package.json").is_file() and (app / "workshopLoader.js").is_file():
                candidates.append(app)
    if len(candidates) != 1:
        raise ValueError("Specify the game installation path; could not identify one Workshop-capable installation")
    return candidates[0]


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Workshop adaptation anchor changed: {old[:80]}")
    return text.replace(old, new, 1)


def replace_function(text, name, replacement):
    text, count = re.subn(r"^function " + name + r"\([^\n]*\) \{\n.*?^\}",
                          lambda _: replacement, text, flags=re.M | re.S)
    if count != 1:
        raise ValueError(f"Expected one function: {name}")
    return text


def adapt_runtime(js):
    # Node fs bypasses Electron's file:// Workshop interceptor. Import the
    # generated data as JS instead, synchronously and without require/IPC.
    data = {p.name: json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((js / "locale").glob("*.json"))}
    (js / "wsr-workshop-data.js").write_text(
        "// Generated locale data, loaded through the Workshop overlay.\n"
        "const data = " + json.dumps(data, ensure_ascii=False) + ";\n"
        "export function readWorkshopJson(name) {\n"
        "    return Object.prototype.hasOwnProperty.call(data, name) ? data[name] : null;\n"
        "}\n", encoding="utf-8", newline="\n")
    for name in ("dom-translate-hook.js", "glossary-tooltip.js", "template-translate.js"):
        p = js / name
        text = p.read_text(encoding="utf-8")
        for line in text.splitlines(keepends=True):
            if line.startswith(("const _require =", "const fs =", "const path =",
                                "const _fs =", "const _path =")):
                text = replace_once(text, line, "")
        text = "import { readWorkshopJson } from './wsr-workshop-data.js';\n" + text
        if name == "template-translate.js":
            text = replace_function(text, "readLocaleTemplateData",
                "function readLocaleTemplateData(locale) {\n"
                "    return readWorkshopJson(localeDataFile(locale, 'templates.json'));\n}")
        else:
            text = replace_function(text, "readJsonNear",
                "function readJsonNear(fileName) {\n    return readWorkshopJson(fileName) || {};\n}")
        if name == "dom-translate-hook.js":
            text = replace_function(text, "jsonCandidates", "")
            text = replace_function(text, "findJsonNear",
                "function findJsonNear(fileName) {\n"
                "    return readWorkshopJson(fileName) ? fileName : null;\n}")
            text = replace_once(text, "!fileName || !fs || !path || missingLocaleData.has(locale)",
                                "!fileName || missingLocaleData.has(locale)")
            text = replace_once(text,
                "    if (!fs || !path) return (captureExclusionsCache = { tickers: new Set(), companyNames: new Set() });\n", "")
        if re.search(r"\b(?:fs|_fs|_path|__dirname|_require)\b", text):
            raise ValueError(f"Disk-dependent data loader remains in {name}")
        p.write_text(text, encoding="utf-8", newline="\n")

    p = js / "locale/localeManager.js"
    text = p.read_text(encoding="utf-8")
    begin = text.index("// WSR localization: register every locale")
    end = text.index("// Initialize translator instances", begin)
    text = ("import { readWorkshopJson } from '../wsr-workshop-data.js';\n" + text[:begin]
            + "// Register the locales bundled with this Workshop item.\n"
            + "for (const [code, cfg] of Object.entries(readWorkshopJson('wsr-locales.json'))) {\n"
            + "    if (!LANGUAGE_OPTIONS[code]) {\n"
            + "        LANGUAGE_OPTIONS[code] = { name: cfg.name || code, dictionary: {}, warning: cfg.warning || '' };\n"
            + "    }\n}\n\n" + text[end:])
    p.write_text(text, encoding="utf-8", newline="\n")


def original_bytes(app, entry):
    # An existing developer/player installation is not a clean source. Only
    # use files (including our backups) that match the manifest's original hash.
    for base in (app, *(app / name for name in
                  ("wsr-kr-player-backup", "wsr-kr-developer-backup", "wsr-kr-user-backup"))):
        p = base / entry["path"]
        if p.is_file():
            raw = p.read_bytes()
            if sha256(raw) == entry["original_sha256"]:
                return raw, str(p)
    raise ValueError(f"No supported original for {entry['path']}; supply a clean supported game or verified backup")


def build(app, output, locale, source=SOURCE):
    app, output = Path(app).resolve(), Path(output).resolve()
    if (app / "resources/app").is_dir():
        app = app / "resources/app"
    if output == app or output.is_relative_to(app) or app.is_relative_to(output):
        raise ValueError("Output must not overlap the game")
    if output.exists():
        raise ValueError("Output already exists; choose a new output folder (preserves published item IDs)")
    patches = load_manifest(TOOLS / "patch_manifest.json")
    originals = [(entry, *original_bytes(app, entry)) for entry in patches["files"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".workshop-build-", dir=output.parent) as temp:
        temp = Path(temp).resolve()
        assert temp.is_relative_to(output.parent)  # cleanup stays inside staging parent
        player, release = temp / "player", temp / "release"
        subprocess.run([sys.executable, str(TOOLS / "build_user_release.py"),
                        "--source", str(source), "--locale", locale, "--output", str(player)], check=True)
        content = release / "content"
        shutil.copytree(player / "game_files", content)
        for entry, raw, _ in originals:
            dest = content / entry["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            apply_entry(content, entry)
        adapt_runtime(content / "js")
        notices = content / "wsr-localisation-notices"
        notices.mkdir()
        for name in ("LICENSE", "LICENSE-DATA.md"):
            shutil.copy2(ROOT / name, notices / name)
        (notices / "GAME-CONTENT.txt").write_text(
            "The modified game UI files remain the property of their original rights holders.\n"
            "The localisation project's licenses apply only to its code and translations.\n"
            "Requires a legitimate copy of Wall Street Raider.\n", encoding="utf-8")
        hashes = {p.relative_to(content).as_posix(): sha256(p.read_bytes())
                  for p in sorted(content.rglob("*")) if p.is_file()}
        (release / "build-report.json").write_text(json.dumps({
            "locale": locale, "content_sha256": hashes,
            "original_sources": {entry["path"]: source for entry, _, source in originals},
            "original_sha256": {e["path"]: e["original_sha256"] for e in patches["files"]},
            "game_version": json.loads((app / "package.json").read_text(encoding="utf-8"))["version"]
                if (app / "package.json").exists() else "unknown",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shutil.copy2(TOOLS / "WORKSHOP.md", release / "UPLOAD.md")
        if locale == "ko-KR":
            shutil.copy2(TOOLS / "workshop-description.ko.txt", release / "description.ko.txt")
        else:
            (release / "description.txt").write_text(
                f"Wall Street Raider localisation: {locale}\n\n"
                "Subscribe, restart the game, then select the language in Settings.\n"
                "Requires a compatible game version. Other UI mods may conflict.\n"
                "Review translation coverage before publishing.\n"
                "Nain Urbain 이영찬 and contributors\n"
                "https://github.com/NainUrbain/WSR_Localisation_kit\n", encoding="utf-8")
        # Copy out so Windows inherits the workspace ACL, not tempfile's
        # deliberately private ACL (which a rename would retain).
        shutil.copytree(release, output)
    print(f"WORKSHOP: {output / 'content'} ({len(hashes)} files)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", nargs="?", help="Game directory or resources/app (read only); auto-detect if omitted")
    parser.add_argument("--locale", default="ko-KR")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dist = (TOOLS if TOOLS.name == "dist_build" else ROOT) / "dist"
    build(args.game or find_game(), args.output or dist / f"workshop_{args.locale}", args.locale, args.source)


if __name__ == "__main__":
    main()
