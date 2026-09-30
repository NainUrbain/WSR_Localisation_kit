# WSR_Localisation_kit — Localization Framework for Wall Street Raider

| I want to… | Download |
| --- | --- |
| **Play Wall Street Raider in Korean** (한국어로 플레이하기) | [Korean patch v1.0.0](https://github.com/NainUrbain/WSR_Localisation_kit/releases/tag/ko-v1.0.0) — `WSR_KR_user.exe` |
| **Translate the game into another language** | [Localisation Kit v0.1.0 Beta](https://github.com/NainUrbain/WSR_Localisation_kit/releases/tag/kit-v0.1.0-beta) — `WSR_Localisation_Kit.zip` |

WSR_Localisation_kit is a multilingual localization framework for Wall Street Raider that grew out of the WSR_KR Korean translation patch. It translates the interface, reports, news, help text, and the sentences the game generates at runtime.

> The source repository and installer releases do not include complete game source files. The optional Workshop builder produces nine modified UI files locally from a legitimate game installation; these retain their original rights. No game executable is included.

## Language status

| Language | Translation | Verification |
| --- | --- | --- |
| Korean (`ko-KR`) | Complete (about 5,200 strings); included as the reference translation | Automated tests and in-game play |
| Japanese (`ja-JP`) | Empty — language settings and rule example only | Automated tests of sample sentences only |
| French (`fr-FR`) | Empty — language settings and rule example only | Automated tests of sample sentences only |

The automated tests (`python -m unittest discover -s wsr_package_build/tests` and `node --experimental-vm-modules wsr_package_build/tests/runtime.test.cjs`) cover the pipeline, the installer, and representative sentences rendered by each language's rules. They do not replace playing the game: fonts, wrapping, and text the tests never see can only be checked in-game.

## Key features

- Translation of menus, dialogs, financial screens, news, advisory and research reports, earnings reports, and other text the game builds at runtime
- Sentence templates that capture changing values (companies, industries, countries, amounts, dates) and let each language choose its own word order
- Per-language grammar rules: Korean particles, French articles and contractions, dates and possessives
- Grammar-aware templates backed by locale data: captured values can carry gender, number, and translator-defined forms, allowing a template to choose variants such as masculine/feminine agreement, locale-specific plural categories, or genitive/dative spellings. Translators supply every variant and the framework selects among them; it does not generate inflections automatically
- Tooltips for financial terms and report column headers
- An in-game editor for translating and previewing text while playing

## Getting started

Translators and maintainers need Python 3.10 or later to run the localization pipeline, which otherwise uses only the standard library. In-game testing also requires a Windows Steam installation of Wall Street Raider matching the version in the current patch manifest. Creating installer executables requires PyInstaller. Players using a prebuilt player installer do not need Python.

**1. Choose or add a language.** Set `$locale` to a code registered in `wsr_package_build/locale_profiles.json` and use it throughout the commands below:

```powershell
$locale = "LOCALE_CODE" # replace with the locale you are working on
```

To add a language, register it in `locale_profiles.json`, optionally add a grammar rules module, then create its folder with `pipeline.py init-locale --locale $locale`. No engine change is needed. See [Register a new language](wsr_package_build/MULTILINGUAL.md#register-a-new-language-or-regional-variant).

**2. Install the framework into your game.** Clone this repository or download it as a ZIP, then run:

```powershell
python .\wsr_package_build\pipeline.py install --locale $locale
```

`install` builds the runtime data and copies it into the auto-detected Steam copy (pass the game's `resources\app` directory to choose one). It checks the game files' SHA-256 hashes first and stops without changing anything if the version is not supported. The game's language menu then lists every registered language.

**3. Translate.** Translations are CSV files in `wsr_package_build/locales/<locale>/` with `Key`, `Source (EN)`, and your `Target (..)` column; a blank target falls back to English.

- In the game, press `Shift+Backtick` to open the developer overlay and set its CSV folder to `wsr_package_build\locales\<locale>`. Hover over text the overlay has tagged and press `F2` to edit its translation; the screen updates immediately.
- `python .\wsr_package_build\pipeline.py check --locale $locale` validates your CSVs.
- `build` only regenerates the runtime data inside this repository. To make the game load your translations after a restart, run `install --locale $locale` again.

The [translation guide](wsr_package_build/MULTILINGUAL.md) explains the template syntax, grammar selectors, word tables, report headers, and the in-game editor.

**4. Release to players.** With PyInstaller installed (`python -m pip install pyinstaller`):

```powershell
.\dist_build\2_build_player_release.bat $locale
```

For most locales this creates `dist_build\dist\WSR_<locale>_user.exe`; the Korean build keeps the historical name `WSR_KR_user.exe`. It is a stand-alone installer with only that language and without the developer overlay. Players close the game, run the installer, and select the language in the game's settings. The installer is unsigned, so Windows SmartScreen may warn; tell players to choose **More info → Run anyway** only for a file downloaded from your release page.

Building installers and updating the patch for a new game version are covered in [MAINTAINING.md](MAINTAINING.md).

## How the patch works

For a native Steam Workshop overlay, see [Workshop build and upload](dist_build/WORKSHOP.md).
The builder outputs a `content/js/` tree and bundles locale data as a JavaScript
module so it loads through the game's Workshop protocol without a separate installer.
Generated game-derived files stay outside source control in `dist_build/dist/`.

The patch modifies nine files in the game's `js/` folder (`api.js`, `app.js`, `locale/localeManager.js`, and six files in `components/`) and adds the translation runtime next to them. `patch_manifest.json` holds only the changed lines, never copies of the game files. Before changing anything the installer verifies each file's SHA-256 hash and backs up the originals to `wsr-kr-developer-backup/` (developer build) or `wsr-kr-player-backup/` (player installer).

**A game update will very likely break the patch.** The installer then refuses to run until the patch manifest is updated for the new game version.

## Uninstallation

- **Developer build:** `python .\wsr_package_build\install_patch.py uninstall "<game>\resources\app"` restores the backed-up originals.
- **Player installer, or if the backup is gone:** run Steam's **Verify integrity of game files**. The files the patch added are then no longer loaded; the full list is in [MAINTAINING.md](MAINTAINING.md#files-added-to-the-game).

Save files are never touched.

## Known limitations

- Coverage depends on what was seen in the game. The translation data was built by capturing the text shown on screen during play, so text that was never seen or captured — rare events, unusual situations — will most likely stay in English.
- A game update will very likely break the patch until the manifest is updated.
- Numeric and currency formatting remains based on the game's English formats. Fixed-width report and table headers stay in English because translating them in place would break column alignment; localized header meanings are provided as hover tooltips instead.
- The translations were built with the US dollar as the game currency. Choosing another currency in the game's settings may leave sentences that contain amounts untranslated or partly translated.
- Renaming your player or rival companies may break the recognition of sentences that contain those names, leaving them untranslated or mistranslated. The default names are the safest choice.
- Translation keys do not interact directly with game data. They are labels that identify what each translation row represents; changing a key does not change the corresponding game data or behavior.
- Some news-event text contains opaque tokens such as `@HUMOR` and `@TEXTSTRING` whose generated values and exact meanings cannot be determined reliably. News-event strings that depend on these tokens are therefore not included as translatable rows in the CSV files.
- Long table or button labels may wrap differently depending on font metrics and window size.
- The `Context` column of the English catalog is still empty. Context notes are a welcome contribution.

## License

- Code: [PolyForm Noncommercial 1.0.0](LICENSE). Free to use, modify, and share for noncommercial purposes; keep the `Required Notice` line (`Copyright 2026 Nain Urbain 이영찬`).
- Translations: [CC BY-NC 4.0](LICENSE-DATA.md). Credit "Nain Urbain 이영찬" and keep derived translations non-commercial.
- Commercial use of either requires a separate license from the copyright holder.

## Permission and unofficial-project notice

WSR_Localisation_kit is an unofficial localization framework for Wall Street Raider, distributed free of charge with permission from the game's creator.
