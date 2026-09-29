"""Public multilingual translation pipeline.

    python pipeline.py init-locale --locale fr-FR
    python pipeline.py check [--locale LOCALE]
    python pipeline.py build [--locale LOCALE]
    python pipeline.py install [GAME_APP_DIR] [--locale LOCALE]
    python pipeline.py rename-key OLD_KEY NEW_KEY

Every locale (locale_profiles.json) goes through the same steps:
pipeline_tools/locale_framework.py checks the translations and
pipeline_tools/runtime_data.py generates game_files/js/locale/<prefix>-*.json.
"""

import csv
import glob
import json
import os
import re
import subprocess
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_TOOLS_DIR = os.path.join(SCRIPT_DIR, "pipeline_tools")
COMMANDS = {"init-locale", "check", "build", "install", "rename-key"}
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
DEFAULT_LOCALE = "ko-KR"

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, SCRIPT_DIR)
from install_patch import find_steam_app_dir  # noqa: E402


def run_tool(name, *args, check=True):
    tool_path = os.path.join(PIPELINE_TOOLS_DIR, name)
    command = [sys.executable, tool_path, *args]
    print(f"\n$ {' '.join(command)}")
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        command,
        cwd=SCRIPT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_env,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    if result.returncode != 0 and check:
        raise SystemExit(f"step failed: {' '.join(command)}")
    if result.returncode != 0:
        print(f"  WARNING: validation reported existing data debt (exit {result.returncode}).")
    return result.returncode


def run_locale_tool(command, locale):
    return run_tool("locale_framework.py", command, "--locale", locale)


def check_csvs(locale, *, repair_headers):
    print("=== check CSV headers ===")
    header_args = ("--locale", locale) if repair_headers else ("--check", "--locale", locale)
    run_tool("fix_csv_header.py", *header_args)
    print("\n=== check canonical translation CSV layout ===")
    run_tool("translation_csvs.py", "--check")


def validate_keys(locale):
    print("\n=== validate translation keys and generated maps ===")
    run_tool("manage_keys.py", "--locale", locale)


def check(locale):
    check_csvs(locale, repair_headers=False)
    print(f"\n=== check {locale} translations ===")
    run_locale_tool("check", locale)
    validate_keys(locale)
    print(f"\nChecks complete for {locale}.")


def build(locale):
    check_csvs(locale, repair_headers=True)
    print(f"\n=== generate {locale} runtime data ===")
    run_locale_tool("build", locale)
    validate_keys(locale)
    print(f"\nBuild complete for {locale}.")


def install(locale, game_app_dir=None):
    build(locale)
    target = game_app_dir or find_steam_app_dir()
    if not target or not os.path.isdir(target):
        raise SystemExit(
            "supported Steam app directory was not found; pass GAME_APP_DIR explicitly"
        )
    installer = os.path.join(SCRIPT_DIR, "install_patch.py")
    command = [sys.executable, installer, "install", target]
    print(f"\n$ {' '.join(command)}")
    subprocess.run(command, cwd=SCRIPT_DIR, check=True)
    print(f"\nInstall complete for {locale}.")


def _csv_column(paths, column):
    for path in paths:
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                value = (row.get(column) or "").strip()
                if value:
                    yield value


def rename_key(old, new):
    """Rename a shared key in the source catalog and every locale.

    Records the rename in key_migrations.csv, applies it with
    manage_keys.py --write (catalog, locales, sidecars, runtime data), then
    refreshes every locale so the row moves to the category file its new
    prefix belongs to.
    """
    catalog = set(_csv_column(glob.glob(os.path.join(SCRIPT_DIR, "source_data", "WSR_translation_*.csv")), "Key"))
    migrations = os.path.join(SCRIPT_DIR, "key_migrations.csv")
    retired = set(_csv_column([migrations], "Old Key"))
    if not KEY_RE.match(new):
        raise SystemExit(f"invalid key {new!r}: use letters, digits, '_', '-' or '.'")
    if old not in catalog:
        raise SystemExit(f"key not found in source_data: {old!r}")
    if new in catalog or new in retired:
        raise SystemExit(f"key already used (active or retired): {new!r}")
    folded = {key.lower() for key in catalog if key != old}
    if new.lower() in folded:
        raise SystemExit(f"key differs from an existing key only by case: {new!r}")

    with open(migrations, "rb") as f:
        ends_with_newline = f.read().endswith(b"\n")
    with open(migrations, "a", encoding="utf-8", newline="") as f:
        if not ends_with_newline:
            f.write("\n")
        csv.writer(f, lineterminator="\n").writerow([old, new, "renamed with pipeline.py rename-key"])
    print(f"=== rename {old} -> {new} ===")
    run_tool("manage_keys.py", "--write")
    with open(os.path.join(SCRIPT_DIR, "locale_profiles.json"), encoding="utf-8") as f:
        locales = list(json.load(f))
    for locale in locales:
        run_locale_tool("init", locale)
    print(f"\nRenamed {old} -> {new} in source_data and {len(locales)} locale(s).")


def parse_args(args):
    locale = DEFAULT_LOCALE
    cleaned = []
    index = 0
    while index < len(args):
        if args[index] == "--locale":
            if index + 1 >= len(args):
                raise SystemExit("--locale requires a locale code")
            locale = args[index + 1]
            index += 2
        else:
            cleaned.append(args[index])
            index += 1
    if cleaned == ["--no-deploy"] or not cleaned:
        return "build", None, locale
    if cleaned[0] in COMMANDS:
        command = cleaned[0]
        rest = cleaned[1:]
        if command in {"init-locale", "check", "build"} and rest:
            raise SystemExit(f"usage: pipeline.py {command} [--locale LOCALE]")
        if command == "install" and len(rest) > 1:
            raise SystemExit("usage: pipeline.py install [GAME_APP_DIR] [--locale LOCALE]")
        if command == "rename-key":
            if len(rest) != 2:
                raise SystemExit("usage: pipeline.py rename-key OLD_KEY NEW_KEY")
            return command, rest, locale
        return command, rest[0] if rest else None, locale
    if len(cleaned) == 1 and not cleaned[0].startswith("-"):
        return "install", cleaned[0], locale
    raise SystemExit(
        "usage: pipeline.py [init-locale|check|build|install [GAME_APP_DIR]] "
        "[--locale LOCALE]"
    )


def main():
    command, operand, locale = parse_args(sys.argv[1:])
    if command == "init-locale":
        run_locale_tool("init", locale)
    elif command == "rename-key":
        rename_key(*operand)
    elif command == "check":
        check(locale)
    elif command == "build":
        build(locale)
    else:
        install(locale, operand)


if __name__ == "__main__":
    main()
