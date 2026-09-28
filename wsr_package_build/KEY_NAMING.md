# Translation keys

Named keys use lowercase letters, digits and single underscores:
`<domain>_<description>[_<number>]`. Existing domain names such as `mainui`,
`researchreport` and `stockbuy` remain intact so category routing stays stable.

Examples:

- `Mainmenu_delete_save_title` → `mainmenu_delete_save_title`
- `tutorial_1-10_body` → `tutorial_1_10_body`
- `General_CEOofCORP` → `general_ceo_of_corp`
- `Quotes_1` → `quotes_1`

`CT-<hash>`, `UI-<hash>` and `HDR-<id>` are reserved generated identifiers.
Their format is retained for editor capture, filtering and table-header data.
Do not merge different entries merely because their normalized names coincide.
For example, `firemenagement_result` is now
`firemanagement_result_pink_slips`, distinct from `firemanagement_result`.

Every rename is recorded in `key_migrations.csv`. Use
`python pipeline.py rename-key OLD_KEY NEW_KEY` to update the source catalog,
all locales, structured references and generated runtime data together.
Keep the `_review` suffix when renaming a reviewed translation.

Run `python pipeline_tools/translation_csvs.py --sort` to sort all 14 source
CSV files and every locale's translation CSV files. Sorting uses natural key
order (`1`, `2`, `10`); generated CT-/UI- entries come last. Category files
remain defined by `pipeline_tools/translation_csvs.py` and `split_map.json`.
Rebuild the locale runtime data after editing or sorting CSV files.

The September 2026 cleanup renamed 607 keys and sorted 5,203 entries per
catalog. Source text, translations and context were preserved in the source,
Korean, French and Japanese catalogs.
