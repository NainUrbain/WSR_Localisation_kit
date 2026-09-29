"""Validate and apply shared key migrations across the catalog and all locales.

The English catalog is the source of truth. key_migrations.csv records every
retired key so renames do not depend on somebody remembering all generated and
hand-written consumers.  Default mode is read-only validation; --write applies
pending migrations, updates structured sidecar references, and regenerates the
registered locale's runtime data through runtime_data.py.
"""

import csv
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from translation_csvs import tr_open, ALL_CSV, EXTRA_CSVS


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_CSV = ALL_CSV
MIGRATIONS_CSV = os.path.join(SCRIPT_DIR, "key_migrations.csv")
HOOK_JSON = os.path.join(SCRIPT_DIR, "game_files", "js", "locale", "ko-hook-data.json")
TEMPLATE_DATA = os.path.join(SCRIPT_DIR, "game_files", "js", "locale", "ko-templates.json")
STRUCTURED_CSVS = [os.path.join(SCRIPT_DIR, "outlook_combinations.csv")]
STRUCTURED_JSONS = [os.path.join(SCRIPT_DIR, "key_overrides.json")]
OVERRIDE_JS = os.path.join(SCRIPT_DIR, "game_files", "js", "wsr-key-overrides.js")


def load_migrations(path=MIGRATIONS_CSV):
    with tr_open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    direct = {}
    errors = []
    for line, row in enumerate(rows, 2):
        old = (row.get("Old Key") or "").strip()
        new = (row.get("New Key") or "").strip()
        if not old or not new or old == new:
            errors.append(f"{os.path.basename(path)}:{line}: invalid migration {old!r} -> {new!r}")
            continue
        if old in direct and direct[old] != new:
            errors.append(f"{os.path.basename(path)}:{line}: {old!r} has two targets: {direct[old]!r} / {new!r}")
        direct[old] = new

    resolved = {}
    for old in direct:
        seen = []
        key = old
        while key in direct:
            if key in seen:
                errors.append("migration cycle: " + " -> ".join(seen + [key]))
                break
            seen.append(key)
            key = direct[key]
        else:
            resolved[old] = key
    return direct, resolved, errors


def _replace_json_values(value, mapping):
    changed = 0
    if isinstance(value, dict):
        for key, child in value.items():
            new_child, count = _replace_json_values(child, mapping)
            value[key] = new_child
            changed += count
        return value, changed
    if isinstance(value, list):
        for i, child in enumerate(value):
            value[i], count = _replace_json_values(child, mapping)
            changed += count
        return value, changed
    if isinstance(value, str) and value in mapping:
        return mapping[value], 1
    return value, 0


def _iter_string_values(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _iter_string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_string_values(child)
    elif isinstance(value, str):
        yield value


def _rewrite_key_csv(path, mapping):
    if not os.path.exists(path):
        return 0
    with tr_open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    if not fields or "Key" not in fields:
        return 0
    changed = 0
    for row in rows:
        old = row.get("Key", "")
        if old in mapping:
            row["Key"] = mapping[old]
            changed += 1
    if changed:
        with tr_open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return changed


def apply_migrations(resolved):
    changes = {}
    locale_csvs = sorted(glob.glob(os.path.join(SCRIPT_DIR, "locales", "*", "WSR_translation_*.csv")))
    for path in [MASTER_CSV] + EXTRA_CSVS + locale_csvs + STRUCTURED_CSVS:
        count = _rewrite_key_csv(path, resolved)
        if count:
            changes[os.path.relpath(path, SCRIPT_DIR)] = count

    structure_path = os.path.join(SCRIPT_DIR, "key_structure.json")
    if os.path.exists(structure_path):
        with open(structure_path, encoding="utf-8") as f:
            structure = json.load(f)
        renamed = {resolved.get(key, key): value for key, value in structure.items()}
        if len(renamed) != len(structure):
            raise ValueError("key migration collides in key_structure.json")
        if renamed != structure:
            with open(structure_path, "w", encoding="utf-8") as f:
                json.dump(renamed, f, ensure_ascii=False, indent=2)
                f.write("\n")

    if os.path.exists(HOOK_JSON):
        with open(HOOK_JSON, encoding="utf-8") as f:
            hook_data = json.load(f)
        hook_keys = hook_data.get("keys", {})
        count = 0
        for source, key in list(hook_keys.items()):
            if key in resolved and resolved[key] != key:
                hook_keys[source] = resolved[key]
                count += 1
        if count:
            tmp = HOOK_JSON + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                json.dump(hook_data, f, ensure_ascii=False, indent=4)
                f.write("\n")
            os.replace(tmp, HOOK_JSON)
            changes[os.path.relpath(HOOK_JSON, SCRIPT_DIR)] = count

    for path in STRUCTURED_JSONS:
        if not os.path.exists(path):
            continue
        with tr_open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        data, count = _replace_json_values(data, resolved)
        if count:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(tmp, path)
            changes[os.path.relpath(path, SCRIPT_DIR)] = count

    if os.path.exists(OVERRIDE_JS):
        with open(OVERRIDE_JS, encoding="utf-8") as f:
            text = f.read()
        count = 0
        for old, new in resolved.items():
            pattern = re.compile(r"(?P<q>['\"])" + re.escape(old) + r"(?P=q)")
            text, n = pattern.subn(lambda m: m.group("q") + new + m.group("q"), text)
            count += n
        if count:
            tmp = OVERRIDE_JS + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            os.replace(tmp, OVERRIDE_JS)
            changes[os.path.relpath(OVERRIDE_JS, SCRIPT_DIR)] = count
    return changes


def validate(resolved, locale=None):
    errors = []
    warnings = []
    with tr_open(MASTER_CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    all_rows = list(rows)
    for path in EXTRA_CSVS:
        with tr_open(path, encoding="utf-8-sig", newline="") as f:
            all_rows.extend(csv.DictReader(f))

    keys = [row.get("Key", "").strip() for row in all_rows if row.get("Key", "").strip()]
    active = set(keys)
    stale = sorted(old for old, terminal in resolved.items() if old != terminal and old in active)
    if stale:
        errors.append("retired keys still active in master CSV: " + ", ".join(stale))
    # Historical targets may themselves be retired when a whole family is
    # reorganized. Active stale keys and generated consumer references are
    # checked separately below; absence alone is expected and not actionable.

    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicates:
        warnings.append(f"{len(duplicates)} pre-existing duplicate key(s): " + ", ".join(duplicates))

    mismatches = []
    candidate_keys = defaultdict(set)
    for row in all_rows:
        source = row.get("Source (EN)", "").strip()
        key = row.get("Key", "").strip()
        if source and key:
            candidate_keys[source].add(key)
    # Validate any built locale, without requiring Korean data to exist.
    from locale_profiles import load_profiles
    generated_refs = []
    profiles = load_profiles()
    if locale and locale not in profiles:
        raise ValueError(f"unknown locale: {locale}")
    for code, profile in profiles.items():
        if locale and code != locale:
            continue
        for suffix, member in (("hook-data.json", "keys"), ("templates.json", "sourceKeys")):
            name = f"{profile['data_prefix']}-{suffix}"
            path = os.path.join(SCRIPT_DIR, "game_files", "js", "locale", name)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                mapping = json.load(f).get(member, {})
            for source, key in mapping.items():
                generated_refs.append((name, key))
                if key not in candidate_keys.get(source.strip(), set()):
                    mismatches.append(f"{name}: {key!r}: {source[:60]!r}")
    if mismatches:
        errors.append(f"{len(mismatches)} generated key-map mismatch(es); first: {mismatches[0]}")

    retired = {old for old, terminal in resolved.items() if old != terminal}
    stale_consumers = []
    for name, value in generated_refs:
        if value in retired:
            stale_consumers.append(f"{name}:{value}")
    for path in STRUCTURED_CSVS:
        if not os.path.exists(path):
            continue
        with tr_open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                value = (row.get("Key") or "").strip()
                if value in retired:
                    stale_consumers.append(f"{os.path.basename(path)}:{value}")
    for path in STRUCTURED_JSONS:
        if not os.path.exists(path):
            continue
        with tr_open(path, encoding="utf-8-sig") as f:
            for value in _iter_string_values(json.load(f)):
                if value in retired:
                    stale_consumers.append(f"{os.path.basename(path)}:{value}")
    if os.path.exists(OVERRIDE_JS):
        with open(OVERRIDE_JS, encoding="utf-8") as f:
            override_text = f.read()
        for old in retired:
            if re.search(r"(['\"])" + re.escape(old) + r"\1", override_text):
                stale_consumers.append(f"{os.path.basename(OVERRIDE_JS)}:{old}")
    if stale_consumers:
        errors.append(
            f"{len(stale_consumers)} retired key reference(s) remain in generated/structured consumers; "
            f"first: {stale_consumers[0]}"
        )

    # A substring label or header definition deliberately repeats the text of
    # a whole-text row, so duplicates only count within one category.
    by_source = defaultdict(set)
    for row in rows:
        source = row.get("Source (EN)", "").strip()
        if source:
            by_source[(row.get("Category", ""), source)].add(row.get("Key", "").strip())
    source_aliases = sum(1 for values in by_source.values() if len(values) > 1)
    if source_aliases:
        warnings.append(f"{source_aliases} source text(s) still have multiple legacy keys")
    return errors, warnings


def main():
    write = "--write" in sys.argv
    _, resolved, errors = load_migrations()
    if errors:
        for error in errors:
            print("ERROR:", error)
        raise SystemExit(1)

    if write:
        changes = apply_migrations(resolved)
        for path, count in changes.items():
            print(f"updated {path}: {count} reference(s)")
        import runtime_data
        for locale in runtime_data.load_profiles():
            runtime_data.write_locale_runtime(locale)
        runtime_data.write_registry(os.path.join(SCRIPT_DIR, "game_files", "js"))
        runtime_data.write_locale_list()
        from locale_framework import refresh_payload_manifest
        refresh_payload_manifest()

    locale = sys.argv[sys.argv.index("--locale") + 1] if "--locale" in sys.argv else None
    validation_errors, warnings = validate(resolved, locale)
    for warning in warnings:
        print("WARNING:", warning)
    if validation_errors:
        for error in validation_errors:
            print("ERROR:", error)
        raise SystemExit(1)
    print(f"key validation passed ({len(resolved)} recorded migration(s))")


if __name__ == "__main__":
    main()
