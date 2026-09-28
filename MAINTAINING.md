# Maintaining WSR_KR

Reference for maintainers: pipeline commands, data layout, installers, game
updates, and keys. Translators only need the
[translation guide](wsr_package_build/MULTILINGUAL.md).

## Pipeline commands

Run from the repository root. Every command takes `--locale` (default `ko-KR`)
and behaves the same for every language.

| Command | What it does |
| --- | --- |
| `pipeline.py check` | Read-only: CSV headers, keys and layout, then translation checks (tokens the English source lacks, out-of-range choice references, language-specific review points) |
| `pipeline.py build` | The same checks, then regenerates the runtime data **inside the repository** (`game_files/js/locale/<prefix>-*.json`, `wsr-locales.json`, the language registry, `payload_manifest.json`) |
| `pipeline.py install [GAME_APP_DIR]` | `build`, then copies the runtime into the game and applies the patch (auto-detects Steam without a directory) |
| `pipeline.py init-locale` | Creates or refreshes `locales/<locale>/` from the English catalog, keeping translations |
| `pipeline.py rename-key OLD NEW` | Renames a shared key everywhere (see [Keys](#keys)) |

`python .\wsr_package_build\pipeline.py` without a command runs `build`.

The developer installer can also be used directly:

```powershell
python .\wsr_package_build\install_patch.py install|status|uninstall "<game>\resources\app"
```

## Tests

```powershell
python -m unittest discover -s wsr_package_build/tests -v
node --experimental-vm-modules wsr_package_build/tests/runtime.test.cjs
```

They use disposable copies and never install into the real game. They cover
source independence, preserved work, stale-source fallback, regional profiles,
installer safety, key renames and layout, and representative sentences for
each language's rules. Finish a release with in-game checks of fonts,
wrapping, reports and language switching.

## Data layout

Inside `wsr_package_build/`:

- `source_data/WSR_translation_*.csv`: the English catalog (`Key`, `Source (EN)`, `Context`), shared by every language
- `locales/<locale>/WSR_translation_*.csv`: translations keyed to the catalog, one file per category (routed by key prefix, `split_map.json`)
- `locales/<locale>/vars/VAR_*.csv`: the locale's word tables (entity names, token values, sectors, label prefixes)
- `locales/<locale>/glossary.csv`: term tooltips
- `reference_data/`: the English side of every `vars/` table, the game's glossary and report header tagging (`header_lines.csv`)
- `locale_profiles.json`: registered locales
- `key_structure.json`: rows the runtime assembles from pieces (fragment families, table headers)
- `key_migrations.csv`: history of renamed keys; `key_overrides.json`: manual text → key assignments for the overlay
- `game_files/js/`: the shared runtime engine (`template-translate.js`, `template-apply.js`, `dom-translate-hook.js`), language rules (`lang-*.js`) and the developer overlay
- `game_files/js/locale/`: generated runtime data — do not edit by hand
- `pipeline_tools/`: checks, runtime generation and key management

Whether a row is an exact text or a sentence template is derived from its
source (an `@TOKEN` or `{choice}`, several lines, or a quote key makes it a
template). `label_*` keys are substrings replaced inside longer lines and
`headerdef_*` keys are report-header tooltips. CSV files are the source of
truth; always go through `pipeline.py` rather than individual generator
modules.

The public build edits and builds existing keys and templates. The
maintainer-only tools for ingesting in-game captures, pruning candidates,
masking new sentences and splitting sentence families are not included.
Developer installs write debug dumps to `wsr_package_build/debug_output/`.

## Keys

Keys are shared by every language. Rename one with
`python .\wsr_package_build\pipeline.py rename-key OLD NEW`, or by editing the
key field in the in-game editor, which runs the same command. It records the
rename in `key_migrations.csv`, updates the catalog, every locale, sidecar
references and generated data, and moves the row to the category file of its
new prefix. Naming rules are in
[KEY_NAMING.md](wsr_package_build/KEY_NAMING.md).

## Building installers

Requires PyInstaller (`python -m pip install pyinstaller`). Generated outputs
are excluded from Git.

```powershell
# Translator kit: every locale's CSVs, the pipeline and the developer overlay
.\dist_build\1_build_translator.bat

# Player installer: one locale, stripped runtime (default ko-KR)
.\dist_build\2_build_player_release.bat fr-FR
```

The translator kit is written to `dist_build\dist\WSR_KR_translator\` and
contains `build_player.bat` so translators without this repository can
package their own player installer. The player builder writes
`dist_build\dist\WSR_<locale>_user.exe` (`WSR_KR_user.exe` for `ko-KR`). The
installer source is `dist_build/install_patch_dist.py`.

## Updating for a new game version

`tools/make_line_patches.py` compares a clean game tree with a separately
prepared modified tree and writes a new patch manifest:

```powershell
python .\tools\make_line_patches.py `
  --mode player `
  --vanilla "D:\SteamLibrary\steamapps\common\Wall Street Raider\resources\app" `
  --modified "D:\work\modified_app" `
  --output ".\dist_build\patch_manifest.json" `
  js/api.js js/app.js js/locale/localeManager.js
```

Do not edit hashes by hand. Review the real differences between the clean and
modified copies, then test installation, status, uninstallation, and
restoration of the original hashes on a disposable copy.

## Files added to the game

After Steam's **Verify integrity of game files** restores the nine patched
files, these added files are no longer loaded and can be left or deleted:

- the `wsr-kr-player-backup/` or `wsr-kr-developer-backup/` folder
- in `js/`: `attachJosa.js`, `dom-translate-hook.js`, `frenchArticles.js`, `glossary-tooltip.js`, `grammar-select.js`, `lang-*.js`, `locale-registry.js`, `template-apply.js`, `template-translate.js`, and the developer build's `localization-capture.js`, `ui-dom-scan.js`, `ws-template-scan.js`, `wsr-*.js`
- in `js/locale/`: `header-lines.json`, `wsr-locales.json`, `wsr-capture-exclusions.json`, and each language's `<prefix>-glossary.json`, `<prefix>-header-glossary.json`, `<prefix>-header-terms.json`, `<prefix>-hook-data.json`, `<prefix>-templates.json`

## Repository layout

```text
├─ README.md, README.ko.md (Korean player guide), MAINTAINING.md
├─ LICENSE (code), LICENSE-DATA.md (translations)
├─ dist_build/          translator/player installer builders and the player installer
├─ tools/               make_line_patches.py (patch deltas)
└─ wsr_package_build/   pipeline, CSVs, runtime engine, developer installer, tests
```
