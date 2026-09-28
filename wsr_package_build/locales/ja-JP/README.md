# Japanese locale

The `WSR_translation_*.csv` files hold the Japanese targets (`Target (JA)`),
one file per category, keyed to the canonical English rows in
`source_data/`. Entity names and words are in `vars/` (fill `target`;
`gender`, `number` and `elision` stay blank), tooltips in `glossary.csv`.

Refresh, validate and build:

```powershell
python ..\..\pipeline.py init-locale --locale ja-JP
python ..\..\pipeline.py check --locale ja-JP
python ..\..\pipeline.py build --locale ja-JP
```

Japanese particles do not change with the preceding word, so write them
directly after a token: `@CORPは@ASSETを売却しました。` Dates render as
`2026年1月5日`; the rules are in `game_files/js/lang-ja.js`.

The game ships its own unfinished Japanese dictionary (`ja-JP.js`), which it
does not load. Once this locale is built, the language menu offers 日本語 and
the text is translated from these files.
