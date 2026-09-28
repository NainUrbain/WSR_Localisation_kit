# Korean locale

These CSVs hold Korean translations keyed to the independent `source_data/`
catalog, just like every other locale. Required columns are `Key`,
`Source (EN)`, `Target (KO)`; optional Context/notes are preserved.

- `WSR_translation_all.csv`: master file
- `WSR_translation_*.csv`: category files, routed by key prefix (`label_*` substring labels, `headerdef_*` report-header tooltips)
- `split_map.json`: key prefix -> category file map (read by the in-game editor)
- `vars/VAR_*.csv`: Korean entity names and words (`target`); `gender`/`number`/`elision` stay blank
- `glossary.csv`: `Term`, `Definition` tooltips (`[!term]` in a translation)

Validate and build:

```powershell
python ..\..\pipeline.py check --locale ko-KR
python ..\..\pipeline.py build --locale ko-KR
```

Korean runtime rules (particles 은/는, 이/가, (으)로 …, dates) live in
`game_files/js/lang-ko.js`, which uses `attachJosa.js`.
