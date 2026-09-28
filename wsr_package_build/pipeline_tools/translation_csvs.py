r"""Expose the split translation CSV files through one read/write stream.

Reads combine the master file and category files. Writes route each row back
to the file selected by its key prefix.

The source catalog stores Key / Source (EN) / Context. Readers going
through tr_open() additionally see virtual Category / Ref / Family columns
(see row_meta()); writers never store them.
"""
import csv
import io
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATION_DIR = os.path.join(SCRIPT_DIR, "source_data")
ALL_CSV = os.path.join(TRANSLATION_DIR, "WSR_translation_all.csv")

# key prefix (lower-case, matched against key.lower()) -> file name (files may repeat)
SPLIT_FILES = {
    "tutorial_": "WSR_translation_tutorial.csv",
    "news_": "WSR_translation_news.csv",
    "advisory_": "WSR_translation_advisory.csv",
    "earningreport_": "WSR_translation_earningreport.csv",
    "cashflow_": "WSR_translation_cashflow.csv",
    "researchreport_": "WSR_translation_researchreport.csv",
    "mainui_": "WSR_translation_mainui.csv",
    "setting_": "WSR_translation_mainui.csv",  # several prefixes may share one file
    "searchui_": "WSR_translation_mainui.csv",
    "prefix_": "WSR_translation_mainui.csv",
    "financial_footnote_": "WSR_translation_researchreport.csv",  # must stay before "financial_" (first match wins)
    "financial_": "WSR_translation_mainui.csv",
    "financialui_": "WSR_translation_mainui.csv",
    "gamestart_": "WSR_translation_mainui.csv",
    "graph_": "WSR_translation_mainui.csv",
    "general_": "WSR_translation_mainui.csv",
    # UI chrome shares the main UI category.
    "actionbar_": "WSR_translation_mainui.csv",
    "command_": "WSR_translation_mainui.csv",
    "mainmenu_": "WSR_translation_mainui.csv",
    "popup_": "WSR_translation_mainui.csv",
    "cheat_": "WSR_translation_mainui.csv",
    "global_": "WSR_translation_mainui.csv",
    "list_": "WSR_translation_mainui.csv",
    # Trading/order dialogs (stocks, futures, bonds, physical commodities,
    # options) -- a large, distinct cluster of its own.
    "stockbuy_": "WSR_translation_trading.csv",
    "stocksell_": "WSR_translation_trading.csv",
    "stockshort_": "WSR_translation_trading.csv",
    "futuresbuy_": "WSR_translation_trading.csv",
    "futuresshort_": "WSR_translation_trading.csv",
    "bondbuy_": "WSR_translation_trading.csv",
    "bondsell_": "WSR_translation_trading.csv",
    "physicalbuy_": "WSR_translation_trading.csv",
    "physicalsell_": "WSR_translation_trading.csv",
    "assetbuy_": "WSR_translation_trading.csv",
    "assetsell_": "WSR_translation_trading.csv",
    "calloptionbuy_": "WSR_translation_trading.csv",
    "calloptionsell_": "WSR_translation_trading.csv",
    "callbuy_": "WSR_translation_trading.csv",
    "callsell_": "WSR_translation_trading.csv",
    "putbuy_": "WSR_translation_trading.csv",
    "putsell_": "WSR_translation_trading.csv",
    "putbuyback_": "WSR_translation_trading.csv",
    "optionbuy_": "WSR_translation_trading.csv",
    "optionsell_": "WSR_translation_trading.csv",
    "optionchain_": "WSR_translation_trading.csv",
    "swap_": "WSR_translation_trading.csv",
    "trade_": "WSR_translation_trading.csv",
    "cryptobuy_": "WSR_translation_trading.csv",
    "cryptosell_": "WSR_translation_trading.csv",
    "indexfuturesbuyback_": "WSR_translation_trading.csv",
    # Corporate finance (bank loans, bond issuance, mergers, contributions,
    # economic/interest-rate report panels).
    "bank_": "WSR_translation_corpfinance.csv",
    "bankloanui_": "WSR_translation_corpfinance.csv",
    "issue_": "WSR_translation_corpfinance.csv",
    "issue_corp_bond_": "WSR_translation_corpfinance.csv",
    "buyback_": "WSR_translation_corpfinance.csv",
    "contribution_": "WSR_translation_corpfinance.csv",
    "merger_": "WSR_translation_corpfinance.csv",
    "economicstat_": "WSR_translation_corpfinance.csv",
    "interestinfo_": "WSR_translation_corpfinance.csv",
    "fund_": "WSR_translation_corpfinance.csv",
    "firemanagement_": "WSR_translation_corpfinance.csv",
    "startup_": "WSR_translation_corpfinance.csv",
    "startcompany_": "WSR_translation_corpfinance.csv",
    "private_": "WSR_translation_corpfinance.csv",
    "law_": "WSR_translation_corpfinance.csv",
    "taxfree_": "WSR_translation_corpfinance.csv",
    "taxable_": "WSR_translation_corpfinance.csv",
    "non_taxable_": "WSR_translation_corpfinance.csv",
    "lawsuit_": "WSR_translation_corpfinance.csv",
    # Named prefixes formerly kept in the unsorted master file.
    "become_": "WSR_translation_corpfinance.csv",  # ETF advisory contracts
    "greenmail_": "WSR_translation_corpfinance.csv",
    "stockoffer_": "WSR_translation_corpfinance.csv",
    "warning_": "WSR_translation_trading.csv",  # thinly-traded caution
    # Semantic prefixes, including key typos as they exist
    # (keys are not renamed here). Auto-generated hash keys (CT-, UI-,
    # NEEDVERIFY-, EA-, GF-, IG-, EF-) carry no topic and stay in all.csv.
    "calloption_": "WSR_translation_trading.csv",
    "callexercise_": "WSR_translation_trading.csv",
    "option_": "WSR_translation_trading.csv",
    "optionbuyback_": "WSR_translation_trading.csv",
    "futures_": "WSR_translation_trading.csv",
    "future_": "WSR_translation_trading.csv",
    "futurebuy_": "WSR_translation_trading.csv",
    "futureshort_": "WSR_translation_trading.csv",
    "futuressell_": "WSR_translation_trading.csv",
    "commodity_": "WSR_translation_trading.csv",
    "crypto_": "WSR_translation_trading.csv",
    "buyphysicalcommodity_": "WSR_translation_trading.csv",
    "physicalcommodity_": "WSR_translation_trading.csv",
    "buystock_": "WSR_translation_trading.csv",
    "stocksells_": "WSR_translation_trading.csv",
    "substocksell_": "WSR_translation_trading.csv",
    "shortcover_": "WSR_translation_trading.csv",
    "bond_": "WSR_translation_trading.csv",
    "advanceoption": "WSR_translation_trading.csv",  # Advanced Options Trading Station
    "liquidate_warning_": "WSR_translation_corpfinance.csv",  # subsidiary liquidation, not futures
    "liquidate_": "WSR_translation_trading.csv",
    "liquidation_": "WSR_translation_corpfinance.csv",
    "overdraft_": "WSR_translation_trading.csv",
    "browse_": "WSR_translation_trading.csv",
    "genereal_": "WSR_translation_trading.csv",
    "error_": "WSR_translation_trading.csv",
    "request_": "WSR_translation_trading.csv",
    "advance_": "WSR_translation_corpfinance.csv",
    "borrow_": "WSR_translation_corpfinance.csv",
    "loans_": "WSR_translation_corpfinance.csv",
    "loan_": "WSR_translation_corpfinance.csv",
    "repay_": "WSR_translation_corpfinance.csv",
    "action_": "WSR_translation_corpfinance.csv",
    "antitrust_": "WSR_translation_corpfinance.csv",
    "harassing_": "WSR_translation_corpfinance.csv",
    "lawfirm_": "WSR_translation_corpfinance.csv",
    "legal_": "WSR_translation_corpfinance.csv",
    "capitalcontr_": "WSR_translation_corpfinance.csv",
    "change_": "WSR_translation_corpfinance.csv",
    "special_": "WSR_translation_corpfinance.csv",
    "changename_": "WSR_translation_corpfinance.csv",
    "ceoelect_": "WSR_translation_corpfinance.csv",
    "ceoresign_": "WSR_translation_corpfinance.csv",
    "resignceo_": "WSR_translation_corpfinance.csv",
    "firemenagement_": "WSR_translation_corpfinance.csv",
    "startcompagny_": "WSR_translation_corpfinance.csv",
    "privateoffering_": "WSR_translation_corpfinance.csv",
    "publicoffering_": "WSR_translation_corpfinance.csv",
    "public_": "WSR_translation_corpfinance.csv",
    "stockissue_": "WSR_translation_corpfinance.csv",
    "stocksplit_": "WSR_translation_corpfinance.csv",
    "stockreversesplit_": "WSR_translation_corpfinance.csv",
    "whiteknight_": "WSR_translation_corpfinance.csv",
    "restructuring_": "WSR_translation_corpfinance.csv",
    "reconstructure_": "WSR_translation_corpfinance.csv",
    "tax_": "WSR_translation_corpfinance.csv",
    "prepay_": "WSR_translation_corpfinance.csv",
    "autopilot_": "WSR_translation_corpfinance.csv",
    "interestinfo": "WSR_translation_corpfinance.csv",
    "lbo_": "WSR_translation_corpfinance.csv",  # these four were hand-placed in
    "recall_": "WSR_translation_corpfinance.csv",  # corpfinance with no prefix
    "replay_": "WSR_translation_corpfinance.csv",  # entry, so --resplit pulled
    "reserve_": "WSR_translation_corpfinance.csv",  # them back into all.csv
    "earnings_": "WSR_translation_earningreport.csv",
    "earning_": "WSR_translation_earningreport.csv",
    "earningdecrease_": "WSR_translation_earningreport.csv",
    "earningdecreased_": "WSR_translation_earningreport.csv",
    "earninginc_": "WSR_translation_earningreport.csv",
    "earningincrease_": "WSR_translation_earningreport.csv",
    "quarter_": "WSR_translation_earningreport.csv",
    "reportreport_": "WSR_translation_earningreport.csv",
    "execoption_": "WSR_translation_earningreport.csv",
    "researchrport_": "WSR_translation_researchreport.csv",
    "research_": "WSR_translation_researchreport.csv",
    "ind_": "WSR_translation_researchreport.csv",
    "financialstatement_": "WSR_translation_researchreport.csv",
    "fianancialui_": "WSR_translation_mainui.csv",
    "finanialui_": "WSR_translation_mainui.csv",
    "financialstab_": "WSR_translation_mainui.csv",
    "load_": "WSR_translation_mainui.csv",
    "loadgame_": "WSR_translation_mainui.csv",
    "save_": "WSR_translation_mainui.csv",
    "gameover_": "WSR_translation_mainui.csv",
    "modal_": "WSR_translation_mainui.csv",
    "steamworkshop_": "WSR_translation_mainui.csv",
    "patchnote_": "WSR_translation_mainui.csv",
    "persprofile_": "WSR_translation_mainui.csv",
    "underbar_": "WSR_translation_mainui.csv",
    "employment_": "WSR_translation_mainui.csv",
    "whoahead_": "WSR_translation_mainui.csv",
    "whosahead_": "WSR_translation_mainui.csv",
    "who_": "WSR_translation_mainui.csv",
    "shareholder_": "WSR_translation_mainui.csv",
    "mkt_": "WSR_translation_mainui.csv",
    "story_": "WSR_translation_mainui.csv",
    "nes_": "WSR_translation_news.csv",
    "headline_": "WSR_translation_news.csv",
    "newstemplate": "WSR_translation_news.csv",
    "tutorrial_": "WSR_translation_tutorial.csv",
    # Substring labels (a short label inside a longer line), see classify().
    "label_": "WSR_translation_labels.csv",
    # Report column-header tooltip definitions, see classify().
    "headerdef_": "WSR_translation_header_glossary.csv",
}
SPLIT_CSVS = [os.path.join(TRANSLATION_DIR, name) for name in dict.fromkeys(SPLIT_FILES.values())]  # unique, in order
TRANSLATION_CSVS = [ALL_CSV] + SPLIT_CSVS  # merged read order
EXTRA_CSVS = [os.path.join(TRANSLATION_DIR, name) for name in (
    "WSR_translation_news_templates.csv", "WSR_translation_table_headers.csv")]
STORED_COLUMNS = ("Key", "Source (EN)", "Context")

# --- row classification ------------------------------------------------------
# A row is a sentence template when its source has an @TOKEN or a {choice},
# spans several lines, or is a quote (quotes are matched inside news blobs);
# everything else is an exact-match label. The rows the Korean generator
# assembles from pieces (fragment families, table headers) are listed in
# key_structure.json with their Category / Ref / Family.
STRUCTURE_JSON = os.path.join(SCRIPT_DIR, "key_structure.json")
VIRTUAL_COLUMNS = ("Category", "Ref", "Family")
_DYNAMIC_RE = re.compile(r"@[A-Z]|\{[^{}]*\}|\[[^\[\]]*\|")
# Quotes (quotehs.prm) are matched inside news blobs and also exported as exact
# matches; they are recognized by key.
_QUOTE_KEY_RE = re.compile(r"^(?:quotes_|event_quote)\d", re.IGNORECASE)
_structure = None


def key_structure():
    global _structure
    if _structure is None:
        _structure = {}
        if os.path.exists(STRUCTURE_JSON):
            with open(STRUCTURE_JSON, encoding="utf-8") as f:
                _structure = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    return _structure


def is_quote_key(key):
    return bool(_QUOTE_KEY_RE.match((key or "").strip()))


def classify(key, source):
    """'Label', 'Candidate Template' or 'UI Label', derived from the row itself.

    label_* keys are substring labels: replaced wherever they occur inside a
    longer line, instead of only as a whole text. headerdef_* keys are
    tooltip definitions for report column headers (reference_data/
    header_lines.csv), never matched as text themselves."""
    source = source or ""
    if (key or "").strip().startswith("label_"):
        return "Label"
    if (key or "").strip().startswith("headerdef_"):
        return "Header Glossary"
    if (_DYNAMIC_RE.search(source) or "\n" in source.strip()
            or is_quote_key(key)):
        return "Candidate Template"
    return "UI Label"


def row_meta(key, source):
    """{'Category', 'Ref', 'Family'} for a row: key_structure.json, else classify()."""
    entry = key_structure().get((key or "").strip())
    if entry:
        return {
            "Category": entry.get("category", ""),
            "Ref": entry.get("ref", ""),
            "Family": entry.get("family", ""),
        }
    return {"Category": classify(key, source), "Ref": "", "Family": ""}

BOM = "﻿"


def _norm(path):
    return os.path.normcase(os.path.abspath(path))


_ALL_NORM = _norm(ALL_CSV)


MANIFEST = os.path.join(TRANSLATION_DIR, "split_map.json")


def write_manifest():
    """source_data/split_map.json: the prefix -> file map, copied to each locale
    debugger (dom-translate-hook.js), which reads/writes this folder directly and
    must route each row to the same file translation_csvs.py would."""
    import json
    data = {
        "_comment": "generated by translation_csvs.py -- do not edit; add prefixes to SPLIT_FILES there",
        "all": os.path.basename(ALL_CSV),
        "prefixes": dict(SPLIT_FILES),
    }
    text = json.dumps(data, ensure_ascii=False, indent=2) + chr(10)
    if not os.path.exists(MANIFEST) or open(MANIFEST, encoding="utf-8", newline="").read() != text:
        with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
            f.write(text)


def path_for_key(key):
    """The CSV a row with this Key belongs to."""
    lowered = (key or "").lstrip(BOM).lower()
    for prefix, name in SPLIT_FILES.items():
        if lowered.startswith(prefix):
            return os.path.join(TRANSLATION_DIR, name)
    return ALL_CSV


def _read_text(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return f.read().decode("utf-8").lstrip(BOM)


def _split_records(text):
    """[(first_field, raw_text)] for every CSV record, raw text kept verbatim."""
    lines = text.splitlines(True)
    reader = csv.reader(iter(lines))
    out, prev = [], 0
    for row in reader:
        raw = "".join(lines[prev:reader.line_num])
        prev = reader.line_num
        if row:
            out.append((row[0], raw))
    return out


def _with_newline(raw):
    return raw if raw.endswith(("\n", "\r")) else raw + "\n"


def merged_text():
    """Header + every row of all.csv and the split files, as one CSV text."""
    records = _split_records(_read_text(ALL_CSV))
    if not records:
        return ""
    parts = [_with_newline(raw) for _, raw in records]
    for path in SPLIT_CSVS:
        rows = _split_records(_read_text(path))
        parts.extend(_with_newline(raw) for _, raw in rows[1:])  # skip header
    return "".join(parts)


def _terminator(path):
    """Record terminator a split file already uses, so rewrites keep it."""
    try:
        with open(path, "rb") as f:
            first = f.readline()
    except FileNotFoundError:
        return "\r\n"
    return "\n" if first.endswith(b"\n") and not first.endswith(b"\r\n") else "\r\n"


def _terminated(raw, terminator):
    # Only the record's own line ending changes; newlines inside quoted
    # cells are left as they are.
    return raw.rstrip("\r\n") + terminator


def distribute(text):
    """Route a full CSV text back to all.csv / the split files by Key prefix."""
    records = _split_records(text)
    if not records:
        raise ValueError("refusing to write an empty translation CSV")
    buckets = {p: [] for p in TRANSLATION_CSVS}
    for key, raw in records[1:]:
        buckets[path_for_key(key)].append(raw)
    for path, rows in buckets.items():
        terminator = _terminator(path)
        body = "".join(_terminated(raw, terminator) for raw in [records[0][1]] + rows)
        payload = (BOM + body).encode("utf-8")
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(payload)
        os.replace(tmp, path)
    write_manifest()


def _annotate(text):
    """Insert the virtual columns after Key in CSV *text*."""
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        return text
    header = [h.strip() for h in rows[0]]
    if "Key" not in header or all(c in header for c in VIRTUAL_COLUMNS):
        return text
    key_i = header.index("Key")
    src_i = header.index("Source (EN)") if "Source (EN)" in header else None
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header[:key_i + 1] + list(VIRTUAL_COLUMNS) + header[key_i + 1:])
    for row in rows[1:]:
        if not row:
            continue
        key = row[key_i] if len(row) > key_i else ""
        source = row[src_i] if src_i is not None and len(row) > src_i else ""
        meta = row_meta(key, source)
        writer.writerow(row[:key_i + 1] + [meta[c] for c in VIRTUAL_COLUMNS] + row[key_i + 1:])
    return out.getvalue()


def _strip_virtual(text):
    """Drop virtual columns from CSV *text* a caller is writing back."""
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        return text
    header = [h.lstrip(BOM).strip() for h in rows[0]]
    drop = {i for i, h in enumerate(header) if h in VIRTUAL_COLUMNS}
    if not drop:
        return text
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n" if "\r\n" in text else "\n")
    for row in rows:
        if row:
            writer.writerow([v for i, v in enumerate(row) if i not in drop])
    return out.getvalue()


def is_translation_csv(path):
    return (
        os.path.normcase(os.path.dirname(os.path.abspath(path))) == os.path.normcase(TRANSLATION_DIR)
        and os.path.basename(path).startswith("WSR_translation_")
        and path.endswith(".csv")
    )


class _SplitWriter(io.StringIO):
    def __init__(self, newline=None):
        super().__init__(newline="")
        self._newline = newline
        self._done = False

    def close(self):
        if not self._done:
            self._done = True
            text = _strip_virtual(self.getvalue().lstrip(BOM))
            if self._newline is None:
                # open("w") with the default newline=None turns every "\n" into
                # os.linesep; keep that so callers behave exactly as before.
                text = text.replace("\n", os.linesep)
            self._commit(text)
        super().close()

    def _commit(self, text):
        distribute(text)


class _FileWriter(_SplitWriter):
    """Writes one translation CSV (not the merged master view)."""

    def __init__(self, path, newline=None):
        super().__init__(newline)
        self._path = path

    def _commit(self, text):
        payload = (BOM + text).encode("utf-8")
        tmp = self._path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(payload)
        os.replace(tmp, self._path)


def _read_view(text, newline):
    """Apply open()'s read-side newline rules to already-merged raw text."""
    if newline is None:  # universal newlines: \r\n and \r both become \n
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    return io.StringIO(text, newline="")


def tr_open(path, mode="r", *args, **kwargs):
    """Drop-in for open(); see module docstring."""
    merged = _norm(path) == _ALL_NORM
    if not merged and not is_translation_csv(path):
        return open(path, mode, *args, **kwargs)
    if "b" in mode:
        raise ValueError("tr_open: binary mode is not supported for the translation CSV")
    newline = kwargs.get("newline")
    if "w" in mode:
        return _SplitWriter(newline) if merged else _FileWriter(path, newline)
    text = merged_text() if merged else _read_text(path)
    if "a" in mode:
        writer = _SplitWriter(newline) if merged else _FileWriter(path, newline)
        writer.write(text)
        writer.seek(0, io.SEEK_END)
        return writer
    return _read_view(_annotate(text), newline)


def resplit():
    """Move every row that belongs in a split file out of all.csv."""
    before = _split_records(merged_text())
    distribute(merged_text())
    after = _split_records(merged_text())
    assert len(before) == len(after), (len(before), len(after))
    return len(after) - 1


def _sort_key(rec):
    """Natural key order, with auto-generated CT-/UI- keys last."""
    key = rec[0].lower()
    parts = tuple(int(part) if part.isdigit() else part
                  for part in re.split(r"(\d+)", key))
    return (key.startswith(("ct-", "ui-")), parts)


def sort_files():
    """Sort canonical and locale CSVs in natural key order; CT-/UI- last.

    The sort is stable (equal keys keep their order) and rows are moved as raw
    text, so nothing is re-quoted.  The header stays on line 1.
    """
    import glob
    paths = TRANSLATION_CSVS + EXTRA_CSVS + sorted(glob.glob(
        os.path.join(SCRIPT_DIR, "locales", "*", "WSR_translation_*.csv")))
    for path in paths:
        records = _split_records(_read_text(path))
        if len(records) < 2:
            continue
        header, rows = records[0], records[1:]
        rows = sorted(rows, key=_sort_key)
        payload = (BOM + "".join(_with_newline(raw) for raw in [header[1]] + [r[1] for r in rows])).encode("utf-8")
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(payload)
        os.replace(tmp, path)
    write_manifest()


def audit_files():
    """Report structural CSV issues without changing translation data.

    Key comparisons are deliberately case-sensitive. The game contains real
    keys that differ only by capitalization, so those pairs are not treated as
    duplicates by this public check.
    """
    errors = []
    warnings = []
    seen = {}
    for path in TRANSLATION_CSVS + EXTRA_CSVS:
        if not os.path.exists(path):
            errors.append(f"missing translation file: {os.path.basename(path)}")
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = set(STORED_COLUMNS)
            fields = set(reader.fieldnames or [])
            extra = sorted(fields - required)
            if extra:
                warnings.append(f"{os.path.basename(path)}: unused column(s) {', '.join(extra)}")
            if not required.issubset(fields):
                errors.append(
                    f"{os.path.basename(path)}: missing columns "
                    + ", ".join(sorted(required - fields))
                )
                continue
            for line, row in enumerate(reader, 2):
                key = (row.get("Key") or "").strip()
                if not key:
                    warnings.append(f"{os.path.basename(path)}:{line}: blank Key")
                    continue
                previous = seen.get(key)
                if previous:
                    errors.append(
                        f"duplicate exact Key {key!r}: {previous} and "
                        f"{os.path.basename(path)}:{line}"
                    )
                else:
                    seen[key] = f"{os.path.basename(path)}:{line}"
                expected = path_for_key(key)
                if path not in EXTRA_CSVS and _norm(expected) != _norm(path):
                    warnings.append(
                        f"{os.path.basename(path)}:{line}: {key!r} belongs in "
                        f"{os.path.basename(expected)}"
                    )
                source = (row.get("Source (EN)") or "").strip()
                if not source:
                    warnings.append(
                        f"{os.path.basename(path)}:{line}: {key!r} has blank source"
                    )
    for message in errors:
        print("ERROR:", message)
    for message in warnings:
        print("WARNING:", message)
    if not errors and not warnings:
        print(f"CSV layout OK: {len(seen)} exact keys across {len(TRANSLATION_CSVS + EXTRA_CSVS)} files")
    else:
        print(f"CSV audit: {len(errors)} error(s), {len(warnings)} warning(s)")
    return not errors


if __name__ == "__main__":
    if "--check" in sys.argv:
        raise SystemExit(0 if audit_files() else 1)
    elif "--sort" in sys.argv:
        sort_files()
        print("sorted every translation CSV by Key (ascending)")
    elif "--resplit" in sys.argv:
        print(f"resplit ok: {resplit()} rows")
    else:
        print(__doc__)
