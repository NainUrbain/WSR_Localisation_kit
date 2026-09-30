# Pipeline tools

Run these through `../pipeline.py`; every step works the same way for every
locale listed in `../locale_profiles.json`.

English keys and context live in `../source_data/`; no locale owns the source
catalog. See `../MULTILINGUAL.md` for the complete workflow and syntax.

- `locale_framework.py`: `init` (create or refresh a locale folder from the
  canonical CSVs, keeping translations), `check` (token, choice and
  language-specific checks) and `build`
- `runtime_data.py`: generates `game_files/js/locale/<prefix>-*.json` from a
  locale's CSV files — templates, fragments, exact matches, labels, entity
  names, token values, label prefixes and tooltips
- `locale_vars.py`: per-locale entity and token-value tables (`vars/`)
- `locale_profiles.py`: profile validation and generated runtime registry
- `grammar_checks.py`: agreement selector syntax and fallback checks
- `locale_<morphology>.py`: extra checks for one language (`locale_fr.py`)
- `translation_csvs.py`: reads/writes the split canonical CSVs and derives
  each row's category (`classify()`, `key_structure.json`)
- `fix_csv_header.py`: header position and BOM check for one locale folder
- `manage_keys.py`: shared-key and historical migration validation

See [key naming and sorting](../KEY_NAMING.md) for the shared naming convention
and the command that sorts both the source catalog and every locale.
