# WSR_KR localization kit

The multilingual localization framework for Wall Street Raider: translation
CSVs, the pipeline that turns them into runtime data, and the developer
overlay for translating in the game. Every language goes through the same
steps; `--locale` picks which one (default `ko-KR`).

Start with [MULTILINGUAL.md](MULTILINGUAL.md): workflow, in-game editor,
template syntax, grammar selectors, word tables and report headers.

## Workflow

```powershell
# Create or refresh a locale folder from the English catalog (keeps translations)
python .\pipeline.py init-locale --locale ja-JP

# Read-only validation
python .\pipeline.py check --locale ja-JP

# Regenerate the runtime data inside this kit (does not touch the game)
python .\pipeline.py build --locale ja-JP

# Build, then copy into the auto-detected Steam copy (or pass the game directory)
python .\pipeline.py install --locale ja-JP
python .\pipeline.py install "D:\SteamLibrary\steamapps\common\Wall Street Raider\resources\app" --locale ja-JP

# Package a player installer for one language (needs PyInstaller)
.\build_player.bat ja-JP
```

Run `install` whenever the game should load your current translations after a
restart. In-game edits made with the overlay are applied live, but only
`install` puts them into the game's files.

## What to translate

In `locales/<locale>/`:

- `WSR_translation_*.csv` — the `Target (..)` column. Keep every `@TOKEN` and
  `{choice}` structure the English uses.
- `vars/VAR_*.csv` — words substituted into sentences (countries, industries,
  assets, commodities, trend words, sectors, label prefixes). Fill `target`;
  languages with grammatical gender also fill `gender`, `number` and optionally
  `elision`.
- `WSR_translation_table_headers.csv`, `WSR_translation_header_glossary.csv` —
  report column headers, shown as tooltips.
- `glossary.csv` — optional term tooltips.

Everything under `game_files/js/locale/` is generated — do not edit it by hand.

## Language rules

Grammar that depends on the substituted value lives in
`game_files/js/lang-<code>.js` (`lang-ko.js`: particles; `lang-fr.js`:
articles and contractions; `lang-ja.js`: the smallest example). Register a new
module with `runtime_module` and `runtime_export` in `locale_profiles.json`;
optional build-time checks go in `pipeline_tools/locale_<code>.py`.

Maintainer topics (installer builds, game updates, data layout, keys) are in
`MAINTAINING.md` of the repository:
https://github.com/sorita1/WSR_Localisation_kit

## License and notice

The code is licensed under PolyForm Noncommercial 1.0.0 (`LICENSE`; keep its
`Required Notice` line). Translations are licensed under CC BY-NC 4.0
(`LICENSE-DATA.md`): credit "Nain Urbain 이영찬" and keep derived translations
non-commercial. Commercial use of either requires a separate license from the
copyright holder. The English game text and the game itself are not covered
by either license.

WSR_KR is an unofficial localization framework for Wall Street Raider,
distributed free of charge with permission from the game's creator. It is not
affiliated with or endorsed by Valve. A legitimate installation of the game
is required.
