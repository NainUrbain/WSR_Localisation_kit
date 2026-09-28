"""Generate a locale's runtime template data (<prefix>-templates.json).

The same code runs for every locale. English source rows come from the
canonical translation CSVs (translation_csvs.TRANSLATION_DIR); the target
text comes from the locale's own CSV files in locales/<locale>/. Output:

- templates:  sentence templates (rows classified "Candidate Template")
- sourceKeys: English source -> CSV Key, for the in-game editor
- fragments:  {FAMILY: {lead|tail|middle: [...]}} from key_structure.json,
              used by the runtime to assemble lead + tail sentences
- values:     token value tables (@HIGHLOW, @SECTOR, ...) from vars/
- entities:   entity names (@COUNTRY, @IND, ...) with gender/number/elision
- prefixes:   report label prefixes ("INDUSTRY OUTLOOK: ") in match order
- entityNames: English entity names per token (same for every locale), used
              to find the boundary between adjacent free-text tokens
"""

import csv
import glob
import json
import os

import locale_vars
from locale_profiles import load_profiles, write_registry

from translation_csvs import (
    ALL_CSV,
    SCRIPT_DIR,
    TRANSLATION_DIR,
    is_quote_key,
    key_structure,
    row_meta,
    tr_open,
)

PROFILE_PATH = os.path.join(SCRIPT_DIR, "locale_profiles.json")
LOCALE_JS_DIR = os.path.join(SCRIPT_DIR, "game_files", "js", "locale")
# Read after the merged master view; rows here are "secondary" when the same
# source also appears in the master view.
EXTRA_CANONICAL = [
    os.path.join(TRANSLATION_DIR, "WSR_translation_news_templates.csv"),
    os.path.join(TRANSLATION_DIR, "WSR_translation_table_headers.csv"),
]
REVIEW_KEY_MARKER = "_review"


def profile_for(locale):
    profile = load_profiles().get(locale)
    if not profile:
        raise SystemExit(f"unknown locale profile: {locale}")
    return profile


def is_review_key(key):
    """A translator marks the intended winner among duplicate sources by
    appending ``_review`` to its key (``_review_`` prefix/suffix also work)."""
    key = (key or "").strip()
    return key.endswith(REVIEW_KEY_MARKER) or key.startswith("_review_") or key.endswith("_review_")


def prefer_reviewed_rows(rows, primary_rows=None):
    """Collapse rows sharing a source: reviewed row first, then the master
    view's last row, then the last row overall. Order of first appearance."""
    grouped, primary_grouped = {}, {}
    for row in rows:
        if row["source"]:
            grouped.setdefault(row["source"], []).append(row)
    for row in primary_rows or []:
        if row["source"]:
            primary_grouped.setdefault(row["source"], []).append(row)
    selected = []
    for source, group in grouped.items():
        primary = primary_grouped.get(source, [])
        reviewed = [r for r in primary if is_review_key(r["key"])]
        if reviewed:
            selected.append(reviewed[-1])
        elif primary:
            selected.append(primary[-1])
        else:
            reviewed = [r for r in group if is_review_key(r["key"])]
            selected.append(reviewed[-1] if reviewed else group[-1])
    return selected


def _read_csv(path):
    with tr_open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_locale_rows(locale):
    """Physical locale rows; never use the source catalog's merged reader here."""
    folder = os.path.join(SCRIPT_DIR, "locales", locale)
    paths = sorted(glob.glob(os.path.join(folder, "WSR_translation_*.csv")))
    legacy = os.path.join(folder, "translations.csv")
    if os.path.exists(legacy):
        paths.append(legacy)
    return [row for path in paths for row in _read_csv(path)]


def stale_targets(locale):
    sources = {r["Key"].strip(): r.get("Source (EN)", "")
               for path in sorted(glob.glob(os.path.join(TRANSLATION_DIR, "WSR_translation_*.csv")))
               for r in _read_csv(path) if r.get("Key")}
    column = profile_for(locale)["target_column"]
    return {r["Key"].strip() for r in read_locale_rows(locale)
            if r.get(column, "").strip() and r.get("Key", "").strip() in sources
            and r.get("Source (EN)", "") != sources[r["Key"].strip()]}


def locale_targets(locale, *, exclude_stale=False):
    """Key -> target text from every CSV in locales/<locale>/."""
    profile = profile_for(locale)
    column = profile["target_column"]
    targets = {}
    stale = stale_targets(locale) if exclude_stale else set()
    for row in read_locale_rows(locale):
        key = (row.get("Key") or "").strip()
        if key and column in row and key not in stale:
            targets[key] = row.get(column) or ""
    return targets


def locale_rows(locale):
    """(primary rows, all rows) as dicts in canonical order."""
    targets = locale_targets(locale, exclude_stale=True)

    def convert(raw):
        key = (raw.get("Key") or "").strip()
        raw_source = raw.get("Source (EN)") or ""
        source = raw_source.strip()
        return {
            "key": key,
            "source": source,
            # Templates keep the cell text verbatim (trailing spaces/newlines
            # are part of what the compiled pattern expects).
            "raw_source": raw_source,
            "target": targets.get(key, "").strip(),
            "raw_target": targets.get(key, ""),
            "category": row_meta(key, source)["Category"],
            "fragments": (key_structure().get(key) or {}).get("fragments", []),
            "standalone": (key_structure().get(key) or {}).get("standalone", True),
        }

    primary = [convert(r) for r in _read_csv(ALL_CSV)]
    extra = []
    for path in EXTRA_CANONICAL:
        if os.path.exists(path):
            extra.extend(convert(r) for r in _read_csv(path))
    return primary, primary + extra


def build_template_data(locale):
    primary, rows = locale_rows(locale)

    def eligible(row):
        return row["category"] == "Candidate Template" and row["target"]

    candidates = prefer_reviewed_rows(
        [r for r in rows if eligible(r)],
        primary_rows=[r for r in primary if eligible(r)],
    )
    # "standalone": false (key_structure.json) keeps a fragment from also
    # matching as a whole sentence (a bare tail such as "poor."); it still
    # gets a source key so the editor can resolve it.
    templates = [
        {"key": r["key"], "source": r["raw_source"], "target": r["raw_target"]}
        for r in candidates if r["standalone"]
    ]

    # Keep source-key metadata even for untranslated rows so a new locale's
    # editor can identify English text before its first translation exists.
    source_candidates = prefer_reviewed_rows(
        [r for r in rows if r["category"] == "Candidate Template"],
        primary_rows=[r for r in primary if r["category"] == "Candidate Template"],
    )
    source_keys = {r["source"]: r["key"] for r in source_candidates if r["key"]}
    source_keys.update({r["source"]: r["key"] for r in candidates if r["key"]})
    for r in rows:
        if (r["source"] and r["key"] and r["source"] not in source_keys
                and r["category"].endswith("Fragment")):
            source_keys[r["source"]] = r["key"]

    fragments = {}
    # Longest source first keeps matcher priority independent of row order.
    for r in sorted(primary, key=lambda row: len(row["source"]), reverse=True):
        if not r["target"]:
            continue
        for tag in r["fragments"]:
            family, role = tag.split(":")
            bucket = fragments.setdefault(family, {}).setdefault(role, [])
            if all(entry["source"] != r["source"] for entry in bucket):
                bucket.append({"key": r["key"], "source": r["source"], "target": r["target"]})

    return {
        "templates": templates,
        "sourceKeys": source_keys,
        "fragments": {family: fragments[family] for family in sorted(fragments)},
    }


def build_hook_data(locale):
    """Exact-match data for dom-translate-hook.js (<prefix>-hook-data.json):

    - exact:     UI labels (and quotes, which are also shown on their own)
    - labels:    substring labels (label_* keys) replaced inside longer lines
    - keys:      English source -> CSV Key, for the in-game editor
    - structure: key_structure.json categories, so live edits classify rows
                 the same way as this build
    """
    primary, rows = locale_rows(locale)

    def ui(row):
        return row["category"] == "UI Label" and row["target"]

    exact = {}
    keys = {r["source"]: r["key"] for r in prefer_reviewed_rows(
        [r for r in rows if r["category"] == "UI Label"],
        primary_rows=[r for r in primary if r["category"] == "UI Label"],
    ) if r["key"]}
    for r in prefer_reviewed_rows([r for r in rows if ui(r)], primary_rows=[r for r in primary if ui(r)]):
        exact[r["source"]] = r["target"]
        if r["key"]:
            keys[r["source"]] = r["key"]
    for r in rows:
        if is_quote_key(r["key"]) and r["target"] and "@" not in r["source"]:
            exact.setdefault(r["source"], r["target"])
    # Labels are matched inside longer lines, so their surrounding spaces count.
    labels = {r["raw_source"]: r["raw_target"] for r in rows if r["category"] == "Label" and r["target"]}
    structure = {key: entry.get("category", "") for key, entry in sorted(key_structure().items())}
    return {"exact": exact, "labels": labels, "keys": keys, "structure": structure}


def _write_json(path, data, indent=1):
    text = json.dumps(data, ensure_ascii=False, indent=indent) + "\n"
    if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)


def write_hook_data(locale):
    """Write game_files/js/locale/<prefix>-hook-data.json; returns its path."""
    profile = profile_for(locale)
    data = build_hook_data(locale)
    path = os.path.join(LOCALE_JS_DIR, f"{profile['data_prefix']}-hook-data.json")
    _write_json(path, data, indent=4)
    print(
        f"{os.path.basename(path)}: {len(data['exact'])} exact, {len(data['labels'])} labels, "
        f"{len(data['keys'])} keys"
    )
    return path


def write_tooltip_data(locale):
    """Glossary / report-header tooltip data for glossary-tooltip.js:

    - <prefix>-glossary.json:        term -> definition (locales/<locale>/glossary.csv)
    - <prefix>-header-glossary.json: English header phrase -> translation
    - <prefix>-header-terms.json:    header phrases tagged inside report text
    - header-lines.json:             whole header lines -> tagged lines (shared
                                     by every locale; reference_data/header_lines.csv)
    """
    profile = profile_for(locale)
    prefix = profile["data_prefix"]
    glossary = {}
    glossary_csv = os.path.join(SCRIPT_DIR, "locales", locale, "glossary.csv")
    if os.path.exists(glossary_csv):
        for row in _read_csv(glossary_csv):
            term, definition = (row.get("Term") or "").strip(), (row.get("Definition") or "").strip()
            if term and definition:
                glossary[term] = definition
    _, rows = locale_rows(locale)
    header_rows = [r for r in rows if r["category"] == "Table Header" and r["target"]]
    header_glossary = {r["source"]: r["target"] for r in header_rows}
    header_glossary.update(
        {r["source"]: r["target"] for r in rows if r["category"] == "Header Glossary" and r["target"]}
    )
    # Longest first so a longer phrase is tagged whole before a shorter one inside it.
    header_terms = sorted({r["source"] for r in header_rows}, key=lambda s: (-len(s), s))
    header_lines = {}
    lines_csv = os.path.join(SCRIPT_DIR, "reference_data", "header_lines.csv")
    if os.path.exists(lines_csv):
        with open(lines_csv, encoding="utf-8-sig", newline="") as f:
            header_lines = {r["Line"]: r["Tagged"] for r in csv.DictReader(f) if r.get("Line")}
    outputs = {
        f"{prefix}-glossary.json": glossary,
        f"{prefix}-header-glossary.json": header_glossary,
        f"{prefix}-header-terms.json": header_terms,
        "header-lines.json": header_lines,
    }
    for name, data in outputs.items():
        _write_json(os.path.join(LOCALE_JS_DIR, name), data, indent=2)
    print(
        f"tooltips: {len(glossary)} glossary, {len(header_glossary)} header definitions, "
        f"{len(header_terms)} header terms, {len(header_lines)} header lines"
    )
    return [os.path.join(LOCALE_JS_DIR, name) for name in outputs]


def write_locale_list(locales=None):
    """locale/wsr-locales.json: the languages the game's language menu offers
    (the patched localeManager.js reads it). By default every profile whose
    runtime data has been built."""
    profiles = load_profiles()
    if locales is None:
        locales = [
            code for code, p in profiles.items()
            if os.path.exists(os.path.join(LOCALE_JS_DIR, f"{p['data_prefix']}-hook-data.json"))
        ]
    listing = {code: {"name": profiles[code]["name"], "warning": profiles[code].get("warning", "")}
               for code in locales}
    path = os.path.join(LOCALE_JS_DIR, "wsr-locales.json")
    _write_json(path, listing, indent=2)
    print(f"wsr-locales.json: {', '.join(listing) or '(none)'}")
    return path


def write_locale_runtime(locale):
    """Every runtime file for one locale; returns the written paths."""
    return [write_hook_data(locale), write_template_data(locale), *write_tooltip_data(locale)]


def write_template_data(locale, extra=None):
    """Write game_files/js/locale/<prefix>-templates.json; returns its path."""
    profile = profile_for(locale)
    data = {"locale": locale, "morphology": profile.get("morphology", "")}
    data.update(build_template_data(locale))
    data["values"] = locale_vars.value_tables(locale)
    data["entities"] = locale_vars.entity_data(locale)
    data["prefixes"] = locale_vars.label_prefixes(locale)
    data["entityNames"] = locale_vars.entity_names()
    data.update(extra or {})
    path = os.path.join(LOCALE_JS_DIR, f"{profile['data_prefix']}-templates.json")
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    counts = {family: sum(len(v) for v in roles.values()) for family, roles in data["fragments"].items()}
    print(
        f"{os.path.basename(path)}: {len(data['templates'])} templates, "
        f"{len(data['sourceKeys'])} source keys, {sum(counts.values())} fragment entries"
    )
    return path


if __name__ == "__main__":
    import sys
    write_template_data(sys.argv[1] if len(sys.argv) > 1 else "ko-KR")
