# Maintaining WSR_Localisation_kit

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
installer safety, key and layout validation, and representative sentences for
each language's rules. Finish a release with in-game checks of fonts,
wrapping, reports and language switching.

## Data layout

Translator-facing locale files are documented in
[`DEVELOPER_BUILD.md`](wsr_package_build/DEVELOPER_BUILD.md#what-to-translate).
The remaining maintainer-facing layout inside `wsr_package_build/` is:

- `source_data/WSR_translation_*.csv`: the English catalog (`Key`, `Source (EN)`, `Context`), shared by every language
- `reference_data/`: the English side of every `vars/` table, the game's glossary and report header tagging (`header_lines.csv`)
- `key_structure.json`: rows the runtime assembles from pieces (fragment families, table headers)
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

Keys are shared by every language and should be treated as stable identifiers.
Their naming convention and the generated fallback identifiers are documented
in [KEY_NAMING.md](wsr_package_build/KEY_NAMING.md).

## Building releases

For the Steam Workshop overlay builder, content-folder layout, bundled preview,
and loader integration test, see [Workshop build and upload](dist_build/WORKSHOP.md).
Workshop output includes nine locally generated modified game UI files and must
remain in the ignored release directory, outside source control.

Only the translator kit's developer EXE requires PyInstaller. Player Workshop
builds use the Python standard library. Generated outputs are excluded from Git.

```powershell
$locale = "LOCALE_CODE"

# Translator kit: every locale's CSVs, the pipeline and the developer overlay
.\dist_build\1_build_translator.bat

# Player Workshop content: one locale, stripped runtime
.\dist_build\2_build_player_release.bat $locale
```

The translator kit is written to `dist_build\dist\WSR_KR_translator\` and
contains `build_player.bat` so translators without this repository can
package their own Workshop release. The player builder writes
`dist_build\dist\workshop_<locale>\content` (or `dist/` in a standalone kit).
Optional arguments after the locale are the game directory and a new output
directory. It does not build an EXE. `install_patch_dist.py` remains available
for the historical manual installer workflow.

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
├─ dist_build/          translator kit and player Workshop builders; legacy installer
├─ tools/               make_line_patches.py (patch deltas)
└─ wsr_package_build/   pipeline, CSVs, runtime engine, developer installer, tests
```
