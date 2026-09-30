# Translation keys

Named keys use lowercase letters, digits and single underscores:
`<domain>_<description>[_<number>]`. Existing domain names such as `mainui`,
`researchreport` and `stockbuy` remain intact so category routing stays stable.

Examples include `mainmenu_delete_save_title`, `tutorial_1_10_body`,
`general_ceo_of_corp` and `quotes_1`.

Most catalog rows have a semantic key describing where or how their text is
used. `CT-<hash>` and `UI-<hash>` are generated fallback identifiers for the
remaining strings whose in-game source or output location could not be
identified reliably enough to assign a semantic name. They should remain
stable until that context is known. `HDR-<id>` is a separate generated format
used for table-header tooltip data.

The current 5,203-row catalog contains 4,797 semantic keys, 181 `CT-` keys,
111 `UI-` keys and 114 `HDR-` keys.

Keys are shared by every locale and should be treated as stable identifiers.

Run `python pipeline_tools/translation_csvs.py --sort` to sort all 14 source
CSV files and every locale's translation CSV files. Sorting uses natural key
order (`1`, `2`, `10`); generated CT-/UI- entries come last. Category files
remain defined by `pipeline_tools/translation_csvs.py` and `split_map.json`.
Rebuild the locale runtime data after sorting CSV files.
