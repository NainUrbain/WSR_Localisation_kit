# WSR_Localisation_kit developer build

The multilingual localization framework for Wall Street Raider: translation
CSVs, the pipeline that turns them into runtime data, and the developer
overlay for translating in the game. Every language goes through the same
steps; `--locale` picks which one (default `ko-KR`).

Start with [MULTILINGUAL.md](MULTILINGUAL.md): workflow, in-game editor,
template syntax, grammar selectors, word tables and report headers.

## Workflow

```powershell
$locale = "LOCALE_CODE" # replace with the locale you are working on

# Create or refresh a locale folder from the English catalog (keeps translations)
python .\pipeline.py init-locale --locale $locale

# Read-only validation
python .\pipeline.py check --locale $locale

# Regenerate the runtime data inside this kit (does not touch the game)
python .\pipeline.py build --locale $locale

# Build, then copy into the auto-detected Steam copy (or pass the game directory)
python .\pipeline.py install --locale $locale
python .\pipeline.py install "D:\SteamLibrary\steamapps\common\Wall Street Raider\resources\app" --locale $locale

# Package a Steam Workshop content folder for one language (no PyInstaller)
.\build_player.bat $locale
```

The player output is `dist/workshop_<locale>/content`. Select that folder in
WSR Mod Uploader. The optional second argument is the game installation path;
the third is a new output directory. See `release_tools/WORKSHOP.md` in the kit
or `../dist_build/WORKSHOP.md` in the source repository for upload instructions.

Run `install` whenever the game should load your current translations after a
restart. In-game edits made with the overlay are applied live, but only
`install` puts them into the game's files.

## What to translate

Translation-facing data is organized as follows:

- `locales/<locale>/WSR_translation_*.csv` — translations keyed to the English
  catalog, one file per category as routed by `split_map.json`. Edit the
  `Target (..)` column and keep every `@TOKEN` and `{choice}` structure the
  English source uses.
- `locales/<locale>/vars/VAR_*.csv` — words substituted into sentences (countries, industries,
  assets, commodities, trend words, sectors, label prefixes). Fill `target`;
  languages with grammatical gender also fill `gender`, `number` and optionally
  `elision`.
- `locales/<locale>/WSR_translation_table_headers.csv` and
  `WSR_translation_header_glossary.csv` —
  report column headers, shown as tooltips.
- `locales/<locale>/glossary.csv` — optional term tooltips.
- `locale_profiles.json` — registered locale codes, display names, target
  columns and optional language-rule modules.

Everything under `game_files/js/locale/` is generated — do not edit it by hand.

## Language rules

Grammar that depends on the substituted value lives in
`game_files/js/lang-<code>.js` (`lang-ko.js`: particles; `lang-fr.js`:
articles and contractions; `lang-ja.js`: the smallest example). Register a new
module with `runtime_module` and `runtime_export` in `locale_profiles.json`;
optional build-time checks go in `pipeline_tools/locale_<code>.py`.

Maintainer topics such as installer builds and game updates are in
`MAINTAINING.md` of the repository:
https://github.com/NainUrbain/WSR_Localisation_kit

## License and notice

The code is licensed under PolyForm Noncommercial 1.0.0 (`LICENSE`; keep its
`Required Notice` line). Translations are licensed under CC BY-NC 4.0
(`LICENSE-DATA.md`): credit "Nain Urbain 이영찬" and keep derived translations
non-commercial. Commercial use of either requires a separate license from the
copyright holder.

WSR_Localisation_kit is an unofficial localization framework for Wall Street
Raider, distributed free of charge with permission from the game's creator.
A legitimate installation of the game is required.
