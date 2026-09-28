"""Locale init / check / build — the same steps for every language.

Every locale folder (locales/<locale>/) mirrors the canonical layout:

- WSR_translation_*.csv   Key, Source (EN), Target (<XX>) — one file per
                          category, rows routed by key prefix (split_map.json)
- vars/VAR_*.csv          entity names and token values (locale_vars.py)
- glossary.csv            Term, Definition shown as in-game tooltips

The canonical English rows live in source_data/, independently of any locale.
init-locale creates or refreshes a
locale's files from it without losing existing translations; build writes
the runtime data through runtime_data.py, identical for every locale.
"""

import argparse
import csv
import glob
import hashlib
import importlib
import json
import os
import re
import shutil
from collections import Counter

import locale_vars
import runtime_data
from grammar_checks import SELECTOR, selector_problems, without_selectors
from translation_csvs import MANIFEST, SCRIPT_DIR, TRANSLATION_DIR

GAME_JS_DIR = os.path.join(SCRIPT_DIR, "game_files", "js")
PAYLOAD_MANIFEST = os.path.join(SCRIPT_DIR, "payload_manifest.json")
TOKEN_REF_RE = re.compile(r"@([A-Z]+)(\d+)?")
CHOICE_RE = re.compile(r"\{(?:\[(\d+)\])?([^{}]*)\}")
# Mirrors TOKEN_ALIASES in game_files/js/template-translate.js: a target may
# use the canonical name while the source captured a sibling name.
TOKEN_ALIASES = {
    "HIGHLOW": ["STOCKMOVE", "STOCKTREND", "STOCKTRENDB", "STOCKPAST", "DIRECTION", "UPDOWN",
                "YTDDIR", "CORNDIR", "CRUDEDIR", "EARNSDIR", "RATECHANGE", "IRATEMOVE", "MKTMOVE",
                "MKTGAINVERB", "MKTRISEVERB", "CMDPRICEDIR", "STOCKSMOVE", "METALDIR", "METALMOVE",
                "CRYPTODIR", "FALLTYPE", "SALESTREND", "GDPTREND", "OPEARNTEND", "PRICEMOVE"],
    "VERB": ["SELLVERB", "SEIZEVERB", "VOTEACTION", "DISPOSEACTION", "DIVVERB", "INTENTVERB",
             "IMPACTVERB", "GUIDDIR", "INSUREGROWTH", "FUTACTION", "CROPVERB", "WHEATVERB",
             "BOOMVERB", "SHIPVERB", "CASHACCUMVERB", "CONTRACTVERB", "MKTSTRENGTHVERB",
             "OILPRICEVERB"],
    "ENTITY": ["CORP", "CORPFULL", "PLAYER"],
}


def locale_dir(locale):
    return os.path.join(SCRIPT_DIR, "locales", locale)


def canonical_files():
    return sorted(glob.glob(os.path.join(TRANSLATION_DIR, "WSR_translation_*.csv")))


def morphology_for(profile):
    """pipeline_tools/locale_<morphology>.py (extra checks), or None."""
    name = profile.get("morphology")
    if not name:
        return None
    try:
        return importlib.import_module(f"locale_{name}")
    except ModuleNotFoundError as exc:
        if exc.name != f"locale_{name}":
            raise
        return None


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, lineterminator="\r\n")
        writer.writerow(header)
        writer.writerows(rows)


def init_locale(locale):
    profile = runtime_data.profile_for(locale)
    folder = locale_dir(locale)
    os.makedirs(folder, exist_ok=True)
    column = profile["target_column"]
    old_rows = runtime_data.read_locale_rows(locale)
    old_by_key = {}
    for row in old_rows:
        key = (row.get("Key") or "").strip()
        if key in old_by_key:
            raise ValueError(f"duplicate locale key {key!r}; resolve it before init-locale")
        if key:
            old_by_key[key] = row
    files = canonical_files()
    if not files:
        raise ValueError("source_data is empty or missing")
    active = {key for key, _ in _canonical_keys()}
    retired = [r for r in old_rows if r.get("Key", "").strip() not in active]
    if retired:
        archive = os.path.join(folder, "retired_translations.csv")
        archived = []
        if os.path.exists(archive):
            with open(archive, encoding="utf-8-sig", newline="") as f:
                archived = list(csv.DictReader(f))
        fields = list(dict.fromkeys(k for r in archived + retired for k in r))
        records = {tuple(r.get(k, "") or "" for k in fields) for r in archived + retired}
        _write_csv(archive, fields, sorted(records))
    total = kept = 0
    for path in files:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        out = []
        fields = ["Key", "Source (EN)", column, "Context"]
        for row in rows:
            key, source = row.get("Key") or "", row.get("Source (EN)") or ""
            previous = old_by_key.get(key.strip(), {})
            target = previous.get(column) or ""
            old_source = previous.get("Source (EN)", source)
            # Keep the old source with its target until a human reviews the
            # change. Runtime generation omits these stale translations.
            if target.strip() and old_source != source:
                source = old_source
            kept += bool(target.strip())
            result = dict(previous)
            result.update({"Key": key, "Source (EN)": source, column: target,
                           "Context": row.get("Context") or ""})
            fields.extend(k for k in result if k not in fields)
            out.append(result)
        total += len(out)
        _write_csv(os.path.join(folder, os.path.basename(path)), fields,
                   [[r.get(k, "") for k in fields] for r in out])
    shutil.copyfile(MANIFEST, os.path.join(folder, os.path.basename(MANIFEST)))
    # Obsolete files were archived above; do not leave a second active copy.
    for path in glob.glob(os.path.join(folder, "WSR_translation_*.csv")):
        if os.path.basename(path) not in {os.path.basename(p) for p in files}:
            os.remove(path)
    legacy = os.path.join(folder, "translations.csv")
    if os.path.exists(legacy):
        os.remove(legacy)
    print(f"{locale}: {total} row(s) in {len(files)} file(s); preserved {kept} translation(s)")
    glossary = os.path.join(folder, "glossary.csv")
    if not os.path.exists(glossary):
        _write_csv(glossary, ["Term", "Definition"], [])
    locale_vars.sync_locale_vars(locale)


def token_problems(source, target):
    """(errors, missing) for one row.

    A source token is captured by its base name (@CORP1 and @CORP2 are both
    CORP). A target reference @NAMEn means the n-th captured NAME; a bare
    @NAME takes the next one and, once they run out, repeats the last (the
    runtime does the same). Errors are references with nothing to point at;
    `missing` lists source tokens the target never uses.
    """
    counts = Counter()
    for tokens in _choice_aware_tokens(source):
        counts[tokens[0]] += 1
    referenced = set()
    errors = []
    for name, number in _choice_aware_tokens(target):
        pool_name = name if counts.get(name) else next(
            (alias for alias in TOKEN_ALIASES.get(name, []) if counts.get(alias)), name
        )
        index = int(number) if number else 1
        if index < 1 or counts.get(pool_name, 0) < index:
            errors.append("@" + name + (number or ""))
        referenced.add(pool_name)
    # Formatting-only captures may be intentionally replaced by target-locale
    # layout. DOTS is a variable dot leader used by fixed-width English text.
    omissible_source_tokens = {"DOTS"}
    missing = sorted(
        name for name in counts
        if name not in referenced and name not in omissible_source_tokens
    )
    return errors, missing


def _choice_aware_tokens(text):
    """(name, number) token references as rendered once: only one alternative
    of a {a|b} choice is ever output, so a choice contributes the largest
    single alternative rather than all of them."""
    tokens = [(m.group(1), m.group(2)) for m in TOKEN_REF_RE.finditer(CHOICE_RE.sub(" ", text))]
    for _ref, body in CHOICE_RE.findall(text):
        alternatives = [
            [(m.group(1), m.group(2)) for m in TOKEN_REF_RE.finditer(alt)] for alt in body.split("|")
        ]
        # Per token name, the alternative that uses it most.
        for name in {name for alt in alternatives for name, _ in alt}:
            tokens.extend(max(([t for t in alt if t[0] == name] for alt in alternatives), key=len))
    return tokens


def audit(locale):
    profile = runtime_data.profile_for(locale)
    morphology = morphology_for(profile)
    required = getattr(morphology, "REQUIRED_VAR_COLUMNS", ()) if morphology else ()
    errors, warnings = [], []
    entities = locale_vars.entity_data(locale, required, errors, warnings)
    values = locale_vars.value_tables(locale, required, errors, warnings)
    form_names = {name for table in [*entities.values(), *values.values()]
                  for record in table.values() for name in record.get("forms", {})}

    known = {k for k, _ in _canonical_keys()}
    seen = set()
    if not known:
        errors.append("source_data is empty or missing")
    for path in sorted(glob.glob(os.path.join(locale_dir(locale), "WSR_translation_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required_columns = {"Key", "Source (EN)", profile["target_column"]}
            if not required_columns.issubset(reader.fieldnames or []):
                errors.append(f"{os.path.basename(path)}: missing required columns")
            for line, row in enumerate(reader, 2):
                key = (row.get("Key") or "").strip()
                if not key or key in seen:
                    errors.append(f"{os.path.basename(path)}:{line}: blank or duplicate key {key!r}")
                seen.add(key)
                if key and key not in known:
                    warnings.append(f"{os.path.basename(path)}:{line}: {key!r} is no longer a canonical key "
                                    f"(init-locale archives it)")
    missing = known - seen
    if missing:
        errors.append(f"{len(missing)} source keys missing; run init-locale --locale {locale}")
    for key in runtime_data.stale_targets(locale):
        warnings.append(f"{key}: English source changed; review target and update its Source (EN) cell; omitted from build")

    _, rows = runtime_data.locale_rows(locale)
    translated = [r for r in rows if r["target"]]
    for r in translated:
        where = r["key"]
        for form in re.findall(r":FORM_([A-Z_]+)", r["target"]):
            if form not in form_names:
                errors.append(f"{where}: no VAR record defines form_{form}")
        errors.extend(f"{where}: {message}" for message in selector_problems(r["target"]))
        bad, missing = token_problems(r["source"], without_selectors(r["target"]))
        if bad:
            errors.append(f"{where}: {', '.join(bad)} has no matching token in the English source")
        if missing:
            warnings.append(f"{where}: English token(s) not used in the translation: @{', @'.join(missing)}")
        source_refs = CHOICE_RE.findall(r["source"])
        source_choices = len(source_refs)
        # A fragment may continue its lead's numbering ("{[3]...}" in the source).
        explicit = {int(ref) for ref, _ in source_refs if ref}
        for ref, _body in CHOICE_RE.findall(SELECTOR.sub("", r["target"])):
            if ref and int(ref) > source_choices and int(ref) not in explicit:
                errors.append(f"{where}: references choice [{ref}], but the source has {source_choices}")
        if morphology and hasattr(morphology, "review_target"):
            target_errors, target_warnings = morphology.review_target(without_selectors(r["target"]))
            errors.extend(f"{where}: {message}" for message in target_errors)
            warnings.extend(f"{where}: {message}" for message in target_warnings)
    for message in errors:
        print("ERROR:", message)
    for message in warnings:
        print("WARNING:", message)
    print(f"{locale}: {len(translated)} translated row(s), {len(errors)} error(s), {len(warnings)} warning(s)")
    return not errors


def _canonical_keys():
    for path in canonical_files():
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                key = (row.get("Key") or "").strip()
                if key:
                    yield key, path


def refresh_payload_manifest():
    """Hash every runtime file under game_files/js (what install_patch.py copies)."""
    manifest = {}
    for root, _dirs, files in os.walk(GAME_JS_DIR):
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, GAME_JS_DIR).replace(os.sep, "/")
            with open(path, "rb") as f:
                manifest[rel] = hashlib.sha256(f.read()).hexdigest()
    with open(PAYLOAD_MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(f"payload_manifest.json: {len(manifest)} runtime file(s)")


def build(locale):
    if not audit(locale):
        raise SystemExit("locale build stopped because validation failed")
    runtime_data.write_locale_runtime(locale)
    runtime_data.write_locale_list()
    runtime_data.write_registry(GAME_JS_DIR)
    refresh_payload_manifest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("init", "check", "build"))
    parser.add_argument("--locale", required=True)
    args = parser.parse_args()
    if args.command == "init":
        init_locale(args.locale)
    elif args.command == "check":
        raise SystemExit(0 if audit(args.locale) else 1)
    else:
        build(args.locale)


if __name__ == "__main__":
    main()
