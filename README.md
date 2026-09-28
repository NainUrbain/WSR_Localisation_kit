# WSR_KR — Localization Framework for Wall Street Raider

| I want to… | Download |
| --- | --- |
| **Play Wall Street Raider in Korean** (한국어로 플레이하기) | [Korean patch v1.0.0](https://github.com/sorita1/WSR_Localisation_kit/releases/tag/ko-v1.0.0) — `WSR_KR_user.exe` |
| **Translate the game into another language** | [Localisation Kit v0.1.0 Beta](https://github.com/sorita1/WSR_Localisation_kit/releases/tag/kit-v0.1.0-beta) — `WSR_Localisation_Kit.zip` |

WSR_KR started as a Korean translation patch for Wall Street Raider and has grown into a multilingual localization framework. It translates the interface, reports, news, help text, and the sentences the game generates at runtime. Every language goes through the same pipeline and runtime engine; a language differs only by its data and, when its grammar needs it, a small rules module.

> This project does not redistribute the game executable or complete copies of the original game source. A legitimate installation of Wall Street Raider is required.

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
- Grammar structures for gender/number agreement, plural categories, and named word forms. These are ways for a translator to *express* agreement, not automatic grammar: the translator writes each word form and the selection rules
- Tooltips for financial terms and report column headers
- An in-game editor for translating and previewing text while playing

## Getting started

Requirements: a Windows Steam installation of Wall Street Raider matching the game version in the current patch manifest, and Python 3.10 or later (standard library only).

**1. Install the framework into your game.** Clone this repository or download it as a ZIP, then run:

```powershell
python .\wsr_package_build\pipeline.py install --locale fr-FR
```

`install` builds the runtime data and copies it into the auto-detected Steam copy (pass the game's `resources\app` directory to choose one). It checks the game files' SHA-256 hashes first and stops without changing anything if the version is not supported. The game's language menu then lists every registered language.

**2. Translate.** Translations are CSV files in `wsr_package_build/locales/<locale>/` with `Key`, `Source (EN)`, and your `Target (..)` column; a blank target falls back to English.

- In the game, press `Shift+Backtick` to open the developer overlay and set its CSV folder to `wsr_package_build\locales\<locale>`. Hover over text the overlay has tagged and press `F2` to edit its translation; the screen updates immediately.
- `python .\wsr_package_build\pipeline.py check --locale fr-FR` validates your CSVs.
- `build` only regenerates the runtime data inside this repository. To make the game load your translations after a restart, run `install --locale fr-FR` again.

The [translation guide](wsr_package_build/MULTILINGUAL.md) explains the template syntax, grammar selectors, word tables, report headers, and the in-game editor.

**3. Add a language.** Register it in `wsr_package_build/locale_profiles.json`, optionally add a grammar rules module, then create its folder with `pipeline.py init-locale --locale <locale>`. No engine change is needed. See [Register a new language](wsr_package_build/MULTILINGUAL.md#register-a-new-language-or-regional-variant).

**4. Release to players.** With PyInstaller installed (`python -m pip install pyinstaller`):

```powershell
.\dist_build\2_build_player_release.bat fr-FR
```

This creates `dist_build\dist\WSR_fr-FR_user.exe`, a stand-alone installer with only that language and without the developer overlay. Players do not need Python: they close the game, run the installer, and select the language in the game's settings. The installer is unsigned, so Windows SmartScreen may warn; tell players to choose **More info → Run anyway** only for a file downloaded from your release page.

Building installers, updating the patch for a new game version, and renaming keys are covered in [MAINTAINING.md](MAINTAINING.md).

## How the patch works

The patch modifies nine files in the game's `js/` folder (`api.js`, `app.js`, `locale/localeManager.js`, and six files in `components/`) and adds the translation runtime next to them. `patch_manifest.json` holds only the changed lines, never copies of the game files. Before changing anything the installer verifies each file's SHA-256 hash and backs up the originals to `wsr-kr-developer-backup/` (developer build) or `wsr-kr-player-backup/` (player installer).

**A game update will very likely break the patch.** The installer then refuses to run until the patch manifest is updated for the new game version.

## Uninstallation

- **Developer build:** `python .\wsr_package_build\install_patch.py uninstall "<game>\resources\app"` restores the backed-up originals.
- **Player installer, or if the backup is gone:** run Steam's **Verify integrity of game files**. The files the patch added are then no longer loaded; the full list is in [MAINTAINING.md](MAINTAINING.md#files-added-to-the-game).

Save files are never touched.

## Known limitations

- Coverage depends on what was seen in the game. The translation data was built by capturing the text shown on screen during play, so text that was never seen or captured — rare events, unusual situations — will most likely stay in English.
- A game update will very likely break the patch until the manifest is updated.
- Numbers, currency, and chart month labels keep the game's English formatting (Korean chart labels are the one exception).
- Long table or button labels may wrap differently depending on font metrics and window size.
- The `Context` column of the English catalog is still empty. Context notes are a welcome contribution.

## License

- Code: [PolyForm Noncommercial 1.0.0](LICENSE). Free to use, modify, and share for noncommercial purposes; keep the `Required Notice` line (`Copyright 2026 Nain Urbain 이영찬`).
- Translations: [CC BY-NC 4.0](LICENSE-DATA.md). Credit "Nain Urbain 이영찬" and keep derived translations non-commercial.
- Commercial use of either requires a separate license from the copyright holder.
- Wall Street Raider and its English text are not covered by either license.

## Permission and unofficial-project notice

WSR_KR is an unofficial localization framework for Wall Street Raider, distributed free of charge with permission from the game's creator. The project is not affiliated with or endorsed by Valve. The game name, original content, and related rights remain with their respective owners.
