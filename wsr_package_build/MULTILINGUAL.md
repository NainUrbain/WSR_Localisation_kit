# Multilingual translation guide

Use Python 3.10 or newer. The pipeline uses only the Python standard library.
Player releases are Steam Workshop folders and do not need PyInstaller.
Node is needed only for the automated JavaScript tests.

## Translate an existing language

Run these commands from the kit directory (`wsr_package_build/` in the
repository):

```powershell
$locale = "LOCALE_CODE"                         # registered in locale_profiles.json
python pipeline.py init-locale --locale $locale # create or refresh the locale folder
# Edit locales/<locale>/WSR_translation_*.csv: the Target (..) cells.
python pipeline.py check --locale $locale       # validate
python pipeline.py install --locale $locale     # build and copy into the game
```

`build` only regenerates the runtime data inside the kit; `install` builds and
then copies it into the game. Run `install` whenever the game should load your
current translations after a restart.

Select the same language in the game. Leave a target blank for English
fallback, and keep keys and source cells unchanged during ordinary
translation.

In the extracted translator kit, `build_player.bat $locale` creates
`dist/workshop_<locale>/content`. In the repository use
`dist_build/2_build_player_release.bat $locale`; output is under `dist_build/dist/`.
Pass the game directory as the optional second argument and a new output directory
as the third. Select **content** in WSR Mod Uploader. The package contains the
selected locale, its runtime, and nine modified game UI files; it has no editor.

## In-game editor

The developer overlay is part of the developer build and the translator kit,
not of player Workshop releases.

- **`Shift+Backtick`** opens or closes the overlay: translation coverage, key
  information, CSV search and editing, and diagnostics. Set its CSV folder to
  `locales/<locale>` for the language you are translating; saved rows are then
  applied to the running game immediately. Rows are applied only while the
  game shows that same language.
- **Hover + `F2`** (or right-click) edits the text under the mouse. This works
  on text the overlay has tagged with its key — most translated or
  translatable text, but not every piece of the screen. `Ctrl+Enter` saves,
  `Esc` closes. Clearing a translation keeps the row and falls back to
  English. Keys are shared stable identifiers and should not be changed during
  translation.
- **`📝 Translation Data`** searches and edits complete rows, including event
  and quote templates and table headers.
- **`Ctrl+Shift+Q`** toggles translation on and off for the session, to compare
  with the English original.
- **`Ctrl+Shift+D`** writes a diagnostic dump of the game-state field index to
  `debug_output/`. It does not change the simulation.

Live edits are a preview. Run `install` so they survive a restart during local
testing. Player Workshop builds regenerate their data directly from the CSVs.

## Template syntax

### Tokens

Uppercase `@TOKEN` placeholders capture values from the English source and
place them in the translation: `@CORP`, `@PLAYER`, `@IND`, `@COUNTRY`,
`@COMMODITY`, `@AMOUNT`, `@PCT`, `@MONTH`, `@YEAR`, … Keep every token the
English uses. `@CORP1`/`@CORP2` pick the first/second captured value, so the
order can follow the target language; a bare token used more often than the
source has it repeats the last value.

Entity and word values (`@IND`, `@COUNTRY`, `@ASSET`, …) are translated
through the locale's `vars/` tables, and dates are formatted by the language
rules. What happens right after a token is also up to the language rules:

```text
Source:   @CORP sells @ASSET at @AMOUNT million.
Korean:   @CORP은/는 @ASSET을/를 @AMOUNT M.에 매각했습니다.   particle chosen by the value's final sound
French:   @CORP vend @ASSET:DEF pour @AMOUNT millions.        le/la/l’/les from the word's gender/number
Japanese: @CORPは@ASSETを@AMOUNT百万で売却しました。           particles written as-is
```

The complete token inventory and capture rules are in
[TOKEN_REFERENCE.md](TOKEN_REFERENCE.md).

### Choices: `{a|b|c}`

Curly braces list alternative wordings. The matcher records which English
alternative appeared and uses the alternative at the same position in the
translation:

```text
Source:  The company has {cut|eliminated} its dividend.
French:  La société a {réduit|supprimé} son dividende.
```

- Any number of alternatives may be used; an alternative may contain an
  `@TOKEN`, and `''` is an empty alternative: `{@LOCATION|''}`.
- Choices in the translation correspond to source choices from left to right.
- `{[n]a|b}` follows the nth source choice instead. Use it when the word order
  differs, a source choice is dropped, or one source choice affects a later
  phrase:

```text
Source:  @CORP {sells|liquidates} {@LOCATION|''} @ASSET.
French:  @CORP {[1]cède|liquide} @ASSET:DEF {[2]@LOCATION|''}.
```

- The older compact form `[a/b]` is also supported; its slash must touch both
  alternatives so literal text such as `[ Y / N ]` stays unchanged.

## Source catalog and updates

`source_data/WSR_translation_*.csv` is the language-independent source of
truth: `Key`, `Source (EN)`, `Context`. Maintainers edit the English text and
add useful screen/context notes here. All locales, including Korean, follow
this catalog. Per-locale CSVs require `Key`, `Source (EN)`, and their configured
target column; `init-locale` also copies Context and preserves translator notes.
Existing three-column CSVs remain supported.

Keys are shared by every language and should remain unchanged during ordinary
translation. Clearing a target in the editor preserves its source row.

Run `init-locale` after catalog changes. It preserves translations and optional
note columns. Removed keys are archived in `retired_translations.csv`. Duplicate
locale keys must be resolved first so refresh cannot silently discard work.

When a translated row's English changes, refresh keeps the **old English next
to its old translation**. `check` reports it and `build` omits that target.
Review against `source_data`, update the translation, then replace its Source
(EN) cell with the new source to acknowledge the review. English fallback is
used meanwhile. A matching key alone is not enough to reuse stale text.

## Register a new language or regional variant

Add an entry to `locale_profiles.json`:

```json
"pt-BR": {
  "name": "Português (Brasil)",
  "data_prefix": "pt-BR",
  "target_column": "Target (PT)",
  "morphology": "pt",
  "runtime_module": "lang-pt.js",
  "runtime_export": "PT_RULES",
  "warning": "Tradução em andamento."
}
```

The locale code selects the complete profile: `pt-BR` and `pt-PT` can use
different data and rules. Each data_prefix must be unique (case-insensitive).
Omitting data_prefix defaults to the complete locale code. Existing `ko`,
`fr`, and `ja` prefixes remain compatible.

Create the rules module before running the pipeline:

```javascript
import { BASE_RULES } from './lang-base.js';
export const PT_RULES = {
    ...BASE_RULES,
    // Override month, dateToken, formatDate, monthDay, attach, finish,
    // possessive, clause, etc. only when this language needs them.
};
```

For a locale using only the defaults, omit morphology/runtime_module/
runtime_export; no custom JS is necessary. Several profiles may share one
module, or select different exported rules from the same module. Optional
Python review rules use `pipeline_tools/locale_<morphology>.py`.

Run `init-locale`, translate, `check`, and `build`. The generated
`locale-registry.js` registers the module automatically. Player packaging
follows static relative ES-module imports, including helper modules. Keep
dependencies inside `game_files/js`; dynamic imports and third-party package
dependencies are not packaged by this mechanism.

## Word metadata and inflections

Edit `locales/<locale>/vars/VAR_*.csv`:

| Column | Meaning |
| --- | --- |
| target | Default translated word; blank keeps English |
| gender | `m`, `f`, `n`, or blank |
| number | `sg`, `pl`, or blank; lexical number, not a nearby quantity |
| elision | `auto`, `yes`, `no`, or blank |
| form_PL, form_SG | Optional plural/singular word forms |
| form_GENITIVE, form_DATIVE, … | Optional named forms, uppercase letters/underscores |

Add form columns only when useful. `init-locale` preserves them. Forms are
written by translators; the engine does not invent declensions or translate
words. `@ASSET:FORM_GENITIVE` selects form_GENITIVE. Missing individual forms
fall back to the default word; inspect all words used by a template. Referring
to a form that no word defines is a build error.

Modifiers can be chained: `@ASSET:FORM_PL:DEF` selects the plural spelling
then the French plural article. FORM_PL/FORM_SG update number for subsequent
article modifiers on that token; they do not change other references' metadata.

French supports `:DEF`, `:DE`, `:A`. Set elision=no for aspirated-h exceptions.
Korean particle notation (`@CORP은/는`) is unchanged. Japanese particles are
written literally after tokens.

## Grammar selectors

Ordinary `{a|b}` and `{[2]a|b}` still follow the **English source choice**.
Double braces select wording using **captured values and their metadata**:

```text
Source: The @ASSET is new.
Target: @ASSET:DEF est {{@ASSET.gender|m=nouveau|f=nouvelle|other=moderne}}.

Source: The @ASSET are new.
Target: @ASSET:DEF sont {{@ASSET.agreement|m_pl=nouveaux|f_pl=nouvelles|other=modernes}}.

Source: Buy @COUNT shares.
Target: Acheter @COUNT {{@COUNT.plural|one=action|other=actions}}.

Source: Buy @COUNT @ASSET.
Target: Acheter @COUNT {{@COUNT.plural|one=@ASSET|other=@ASSET:FORM_PL}}.
```

Supported selectors:

| Selector | Branch keys |
| --- | --- |
| `.gender` | `m`, `f`, `n`, `other` |
| `.number` | `sg`, `pl`, `other` |
| `.agreement` | `m_sg`, `f_sg`, `n_sg`, `m_pl`, `f_pl`, `n_pl`, `other` |
| `.plural` | `zero`, `one`, `two`, `few`, `many`, `other`, or an exact number such as `0` |

Plural categories come from `Intl.PluralRules` for the full locale code,
not an English `count == 1` rule. Exact numeric branches take priority.
The game's English comma-grouped numeric captures are accepted. Non-numeric
quantities and absent metadata use `other`, which is required in every selector.

`@ASSET2` selects the second captured asset. Selector references do not consume
tokens; an unnumbered selector always uses the first capture. Branches may
contain tokens and their modifiers, but cannot contain nested selectors,
source choices, literal `|`, or braces. Several separate selectors can appear
in the same sentence.

This is explicit agreement, not automatic grammar correction. Choose the
controlling token and supply the appropriate branch text. Complex language
rules can still be implemented in a rules module. Numeric/currency formatting
and bidirectional layouts are not universally localized by these selectors.
The existing game delta also has Korean-specific chart month labels; chart
canvases for other locales still use the game's English labels. This does
not affect the shared text-template month formatter.

## Report and table headers

Many reports are fixed-width text tables. Translating their column headers
in place would break the column alignment, so header text **stays in
English on screen** and the translation appears as a **tooltip** when the
player hovers over it. There is no length limit: write the full meaning.

| File | Keys | What to write |
| --- | --- | --- |
| `WSR_translation_table_headers.csv` | `HDR-*` | Translation of a column header phrase (`TYPE OF FUTURES` → 선물 종류). Wherever the phrase appears in upper case, it gets this tooltip. |
| `WSR_translation_header_glossary.csv` | `headerdef_*` | Full meaning behind an abbreviated header word (`LOAN` in a loan table means `LOAN AMOUNT` → 대출 금액). |
| `reference_data/header_lines.csv` | — | Maintainers only, shared by every language: which word of a whole header line gets which meaning. |

A tagged line in `header_lines.csv` looks like
`[CREDIT(!CREDIT RATING)]       [LOAN(!LOAN AMOUNT)]`: the text before `(!`
stays on screen, and the text after it is the English source of a row in
either header CSV whose translation becomes the tooltip. Both header CSVs are
ordinary translation files; a blank target means that header simply has no
tooltip.

Tooltips for other financial terms come from `glossary.csv` (`Term`,
`Definition`); write `[!term]` inside a translation to attach one.

## Verification

```powershell
python -m unittest discover -s tests -v
node --experimental-vm-modules tests/runtime.test.cjs
```

Tests cover source independence, preserved work, stale-source fallback,
regional profiles, custom-module packaging, malformed data rejection, and
representative Korean/Japanese/French sentences plus Russian/Arabic plural
categories. They use disposable kits and do not install into the real game.
Finish a release with in-game checks of fonts, wrapping, reports and language
switching; these tests do not replace visual checks.
