import csv
import glob
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



def tracked_csvs(locale):
    """Every translation CSV of one locale folder."""
    folder = os.path.join(SCRIPT_DIR, "locales", locale)
    return sorted(glob.glob(os.path.join(folder, "WSR_translation_*.csv")))


# Plus one "Target (...)" column, whatever the locale.
REQUIRED_COLUMNS = {"Key", "Source (EN)"}


def _header_fields(line):
    """Return a normalized header row, or None when *line* is data.

    Translation CSVs intentionally do not all have the same optional columns,
    and spreadsheet users may reorder or add columns.  Header recognition must
    therefore be based on the required column names rather than one exact byte
    prefix.
    """
    try:
        fields = next(csv.reader([line.lstrip("\ufeff")]))
    except (csv.Error, StopIteration):
        return None
    normalized = [field.strip() for field in fields]
    has_target = any(field.startswith("Target (") for field in normalized)
    return normalized if REQUIRED_COLUMNS.issubset(normalized) and has_target else None


def check_and_fix(path, check_only):
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = f.readlines()
    with open(path, "rb") as f:
        bom_present = f.read(3) == b"\xef\xbb\xbf"

    if not lines:
        print(f"  ! {path} is empty -- skipping.")
        return True

    header_indices = [i for i, line in enumerate(lines) if _header_fields(line) is not None]

    if not header_indices:
        print(f"  ! No header row found at all in {path} "
              f"(required columns: {', '.join(sorted(REQUIRED_COLUMNS))}). "
              "Not safe to auto-fix -- check the file by hand.")
        return False

    if len(header_indices) > 1:
        print(f"  ! Found {len(header_indices)} header-looking rows in {path} "
              f"(at lines {[i + 1 for i in header_indices]}). Not safe to auto-fix -- "
              "check the file by hand (possible duplicate/corrupted header).")
        return False

    idx = header_indices[0]

    if idx == 0 and bom_present:
        print(f"  OK - header already at row 1 ({path}). No fix needed.")
        return True

    if idx == 0 and not bom_present:
        print(f"  Header is at row 1 but the UTF-8 BOM is missing in {path} "
              "(Excel may decode Korean text as the Windows ANSI codepage).")
        if check_only:
            return False
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            f.writelines(lines)
        print(f"  Fixed: added the UTF-8 BOM. ({len(lines)} total lines, unchanged otherwise.)")
        return True

    print(f"  Header row found at line {idx + 1} instead of line 1 in {path}.")
    print("  This almost always means the file got fully sorted (e.g. by a "
          "spreadsheet app's \"sort all columns\" action) with the header "
          "caught up in the sort.")

    if check_only:
        return False

    header_line = lines.pop(idx)
    lines.insert(0, header_line)

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.writelines(lines)

    print(f"  Fixed: moved header back to line 1. ({len(lines)} total lines, unchanged.)")
    return True


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    locale = args[args.index("--locale") + 1] if "--locale" in args else "ko-KR"
    all_ok = True
    for path in tracked_csvs(locale):
        if not os.path.exists(path):
            continue
        ok = check_and_fix(path, check_only)
        all_ok = all_ok and ok
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
