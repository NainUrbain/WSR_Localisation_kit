# French locale

The `WSR_translation_*.csv` files hold the French targets (`Target (FR)`),
one file per category, keyed to the canonical English rows in
`source_data/`. Entity names and words are in `vars/`, tooltips in
`glossary.csv`.

French-specific build checks live in `pipeline_tools/locale_fr.py`; the
runtime rules (articles, contractions, dates) live in
`game_files/js/lang-fr.js` and `game_files/js/frenchArticles.js`.

See [the multilingual guide](../../MULTILINGUAL.md) for gender/number
agreement selectors, quantity-based plurals and named `form_*` inflections.

Create or refresh the working rows without overwriting existing French text:

```powershell
python ..\..\pipeline.py init-locale --locale fr-FR
```

Then validate and build:

```powershell
python ..\..\pipeline.py check --locale fr-FR
python ..\..\pipeline.py build --locale fr-FR
```

French review pays special attention to:

- every source token also appearing in the target;
- source-choice references such as `{[1]...|...}`;
- gender and number around entity tokens;
- elision and contractions before tokens (`de`, `des`, `de la`,
  `de l’`, `au`, `à la`, `aux`, `à l’`). ASCII apostrophes are
  accepted for checking; unaccented `a la` and `a l’` are reported;
- a non-breaking space before `:`, `;`, `!`, and `?`.

Entity tokens use the matching row in `vars/VAR_*.csv` (a copy of
`reference_data/VAR_*.csv` that `init-locale` keeps in sync). The locale
columns are:

- `target`: French token value; blank keeps the English value.
- `gender`: `m` or `f`.
- `number`: `sg` or `pl`.
- `elision`: optional `auto`, `yes`, or `no`. `auto` uses the first letter;
  set `no` for aspirated-h exceptions and `yes` for exceptional elision.

French target templates can request an article or contraction with a token
modifier:

- `@IND:DEF` -> `le`, `la`, `l’`, or `les`
- `@IND:DE` -> `du`, `de la`, `de l’`, or `des`
- `@IND:A` -> `au`, `à la`, `à l’`, or `aux`

The same modifiers work on other VAR-backed tokens such as `@COUNTRY`,
`@REGION`, `@ASSET`, and `@COMMODITY`. A bare token such as `@IND` inserts
only `target`. Missing metadata falls back safely to `de`, `à`, or the bare
value and remains visible to the checker for review.
