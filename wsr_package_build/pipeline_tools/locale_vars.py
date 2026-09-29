"""Per-locale VAR (entity) tables.

reference_data/VAR_*.csv holds the canonical English rows only. Each locale
keeps a copy under locales/<locale>/vars/ with the same canonical columns
plus four locale columns that every language shares:

- target:  translated value; blank keeps the English value
- gender:  m, f, or n; blank when the language has no grammatical gender
- number:  sg or pl; blank when unused
- elision: auto, yes, or no; blank means auto

Languages such as Korean or Japanese simply leave gender/number/elision
blank. A morphology module (locale_<morphology>.py) can declare
REQUIRED_VAR_COLUMNS to have blanks reported as review warnings.
"""

import csv
import os
import re


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_DIR = os.path.join(SCRIPT_DIR, "reference_data")
LOCALE_COLUMNS = ("target", "gender", "number", "elision")
VALID_VALUES = {
    "gender": {"", "m", "f", "n"},
    "number": {"", "sg", "pl"},
    "elision": {"", "auto", "yes", "no"},
}
# Entity records (@COUNTRY, @IND, ...): VAR file -> how a row picks its token(s).
# VAR_entity_names.csv lists every display name the game renders per token.
ENTITY_SOURCES = {
    "VAR_entity_names.csv": ("token", None),
    "VAR_company_industry_country.csv": ("type", {"company": ("CORP", "CORPFULL")}),
}
# Value tables (@HIGHLOW, @SECTOR, ...): VAR file -> how a row picks its table.
VALUE_SOURCES = {
    "VAR_token_values.csv": ("table", None),
    "VAR_sectors.csv": (None, "SECTOR"),
    "VAR_contract_types.csv": (None, "CONTRACT"),
}
PREFIX_FILE = "VAR_label_prefixes.csv"


def vars_dir(locale):
    return os.path.join(SCRIPT_DIR, "locales", locale, "vars")


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def canonical_files():
    return sorted(
        name for name in os.listdir(REFERENCE_DIR)
        if name.startswith("VAR_") and name.endswith(".csv")
    )


def read_locale_vars(locale, filename):
    """Rows of locales/<locale>/vars/<filename>, or [] when the file is absent."""
    path = os.path.join(vars_dir(locale), filename)
    if not os.path.exists(path):
        return []
    return _read(path)[1]


def sync_locale_vars(locale):
    """Create or refresh the locale VAR copies, preserving locale columns."""
    out_dir = vars_dir(locale)
    os.makedirs(out_dir, exist_ok=True)
    total = kept = 0
    for filename in canonical_files():
        canon_fields, canon_rows = _read(os.path.join(REFERENCE_DIR, filename))
        path = os.path.join(out_dir, filename)
        existing = {}
        form_columns = []
        if os.path.exists(path):
            old_fields, old_rows = _read(path)
            form_columns = [c for c in old_fields if c.startswith("form_")]
            for row in old_rows:
                existing[tuple(row.get(c, "") for c in canon_fields)] = row
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=canon_fields + list(LOCALE_COLUMNS) + form_columns, lineterminator="\n"
            )
            writer.writeheader()
            for row in canon_rows:
                old = existing.get(tuple(row.get(c, "") for c in canon_fields), {})
                out = {c: row.get(c, "") for c in canon_fields}
                out.update({c: old.get(c, "") for c in (*LOCALE_COLUMNS, *form_columns)})
                kept += bool(out["target"].strip())
                total += 1
                writer.writerow(out)
    print(f"{locale}: synced {total} VAR row(s); preserved {kept} translated value(s)")


def _group_records(locale, sources, required, errors, warnings):
    """{group: {UPPER English name: record}} from the locale's VAR copies."""
    groups = {}
    for filename, (column, mapping) in sources.items():
        rel = f"locales/{locale}/vars/{filename}"
        path = os.path.join(vars_dir(locale), filename)
        if not os.path.exists(path):
            errors.append(f"{rel}: missing; run init-locale --locale {locale}")
            continue
        fields, rows = _read(path)
        form_columns = [c for c in fields if c.startswith("form_")]
        for column_name in form_columns:
            if not re.fullmatch(r"form_[A-Z_]+", column_name):
                errors.append(f"{rel}: invalid form column {column_name!r}; use form_GENITIVE, form_PL, etc.")
        missing = [c for c in LOCALE_COLUMNS if c not in fields]
        if missing:
            errors.append(f"{rel}: missing column(s) {', '.join(missing)}")
            continue
        for line, row in enumerate(rows, 2):
            if column is None:
                names = (mapping,)
            elif mapping is None:
                names = ((row.get(column) or "").strip(),)
            else:
                names = mapping.get((row.get(column) or "").strip(), ())
            names = tuple(n for n in names if n)
            if not names:
                continue
            values = {c: (row.get(c) or "").strip() for c in LOCALE_COLUMNS}
            for c in ("gender", "number", "elision"):
                values[c] = values[c].lower()
                if values[c] not in VALID_VALUES[c]:
                    allowed = ", ".join(sorted(v for v in VALID_VALUES[c] if v))
                    errors.append(f"{rel}:{line}: {c} must be one of {allowed}")
            source = (row.get("name_en") or "").strip()
            if not source or not (any(values.values()) or any(row.get(c) for c in form_columns)):
                continue
            if values["target"]:
                for c in required:
                    if not values[c]:
                        warnings.append(f"{rel}:{line}: target has no {c}")
            record = {
                "target": values["target"] or source,
                "gender": values["gender"],
                "number": values["number"],
                "elision": values["elision"] or "auto",
            }
            forms = {c[5:]: (row.get(c) or "").strip() for c in form_columns if (row.get(c) or "").strip()}
            if forms:
                record["forms"] = forms
            aliases = [source]
            if filename == "VAR_company_industry_country.csv":
                aliases.append((row.get("extra_en") or "").strip())  # ticker symbol
            for name in names:
                table = groups.setdefault(name, {})
                for alias in aliases:
                    if alias and not alias.startswith("@"):
                        table[alias.upper()] = record
    return groups


def entity_data(locale, required=(), errors=None, warnings=None):
    """Token -> {UPPER English name: record} for entity tokens."""
    errors = errors if errors is not None else []
    warnings = warnings if warnings is not None else []
    return _group_records(locale, ENTITY_SOURCES, required, errors, warnings)


def value_tables(locale, required=(), errors=None, warnings=None):
    """Table -> {UPPER English value: record} for the token value tables."""
    errors = errors if errors is not None else []
    warnings = warnings if warnings is not None else []
    return _group_records(locale, VALUE_SOURCES, required, errors, warnings)


def label_prefixes(locale):
    """[{prefix, target}] in match order; a blank target keeps the English
    label. Cells are used verbatim (the trailing space is part of a prefix)."""
    out = []
    for row in read_locale_vars(locale, PREFIX_FILE):
        prefix = row.get("name_en") or ""
        if prefix:
            out.append({"prefix": prefix, "target": row.get("target") or prefix})
    return out


def entity_names():
    """Token -> English display names (language-neutral), from reference_data."""
    names = {}
    path = os.path.join(REFERENCE_DIR, "VAR_entity_names.csv")
    for row in _read(path)[1]:
        token, name = (row.get("token") or "").strip(), (row.get("name_en") or "").strip()
        if token and name:
            names.setdefault(token, []).append(name.upper())
    return names
