# Runtime Token Reference

This document describes the `@TOKEN` placeholders accepted by the WSR_KR dynamic sentence-template runtime. It reflects the public CSV corpus and `game_files/js/template-translate.js` as audited on 2026-09-24.

For agreement selectors and named inflections added to the shared runtime,
see [MULTILINGUAL.md](MULTILINGUAL.md).

## How a token is processed

Given an English template such as:

```text
@CORP sells @ASSET at @AMOUNT million.
```

the runtime:

1. Converts each token into a capture pattern and matches it against the live English sentence.
2. Normalizes captures whose spelling or number format can vary.
3. Translates known entity names or controlled vocabulary when a lookup exists.
4. Inserts the captured values into `Target (KO)` in the order requested by the Korean template.
5. Resolves Korean particle pairs such as `은/는`, `이/가`, `을/를`, and `로/으로` after substitution.

Numbered forms select occurrences, not different token types. For example, `@CORP1` and `@CORP2` capture the first and second company values and may be reordered freely in the Korean template.

An explicit capture pattern constrains what a token may match. A token without an explicit pattern uses the generic fallback capture, so it remains functional but accepts a broader range of text. If a captured value has no translation lookup, it is preserved exactly rather than removed.

## Entity and name tokens

| Token | Role | Runtime handling |
| --- | --- | --- |
| `@CORP` | Short company name or symbol used by the game | Explicit capture; preserved as the game displays it |
| `@CORPFULL` | Full company name | Explicit capture; preserved |
| `@PLAYER` | Player name | Explicit capture; preserved |
| `@PLAYERSHORT` | Short player label | Generic fallback; preserved |
| `@ENTITY` | Context-dependent company, player, bank, or other entity name | Generic fallback; preserved |
| `@COUNTRY` | Country | Explicit capture; translated through the country lookup when known |
| `@IND` | Industry | Explicit capture; translated through the industry lookup when known |
| `@REGION` | Geographic/economic region | Explicit capture; translated through the region lookup when known |
| `@LOCATION` | Location or production region | Explicit capture; translated through the location lookup when known |
| `@ASSET` | Asset type | Explicit capture; translated through the asset lookup when known |
| `@COMMODITY` | Commodity | Explicit capture; translated through the commodity lookup when known |
| `@CITY` | News dateline or city | Explicit capture; translated through the miscellaneous vocabulary when known |
| `@SECTOR` | Market sector | Explicit capture; translated through the sector vocabulary when known |
| `@CONTRACT` | Contract or supply-contract type | Explicit capture; translated through the contract vocabulary when known |
| `@UW` | Underwriter name or label | Explicit capture; preserved |

## Numbers, dates, and formatting tokens

| Token | Role | Runtime handling |
| --- | --- | --- |
| `@AMOUNT` | Money, price, or another formatted numeric amount | Explicit capture and numeric normalization |
| `@PCT` | Percentage | Explicit capture and percentage normalization |
| `@SHARES` | Share, unit, or contract quantity | Explicit capture and quantity normalization |
| `@SHARE` | Legacy share/contract count | Generic fallback; preserved |
| `@COUNT` | General count | Explicit capture and numeric normalization |
| `@RATIO` | Financial ratio | Explicit capture and ratio normalization |
| `@RATING` | Credit or analyst rating | Explicit capture; intentionally preserved when no vocabulary mapping applies |
| `@YEAR` | Four-digit or contextual year | Explicit capture |
| `@MONTH` | Month name | Explicit capture and month normalization |
| `@MONTHNUM` | Numeric month | Explicit capture |
| `@MONTHDAY` | Month-and-day expression | Explicit capture and date-fragment normalization |
| `@DATE` | Full date | Explicit capture and Korean date formatting |
| `@MONTHS` | Duration in months | Explicit capture and duration normalization |
| `@YEARS` | Duration in years | Explicit capture and duration normalization |
| `@QUARTERS` | Duration or count in quarters | Explicit capture and normalization |
| `@QORD` | Ordinal quarter, such as first or second | Explicit capture and ordinal normalization |
| `@QNUM` | Numeric quarter | Explicit capture |
| `@STEPNUM` | Current/total step or row number | Generic fallback; preserved |
| `@PLAYERNUM` | Player index | Explicit capture; currently unused by the public CSV corpus |
| `@SAVENUM` | Save-slot number | Explicit capture |
| `@MOYR` | Compact month/year option code | Generic fallback; preserved |
| `@DOTS` | Variable dot leader or spacing filler in fixed-width output | Explicit capture; normally omitted from Korean output |

The runtime currently has dedicated normalizers for `AMOUNT`, `SHARES`, `PCT`, `QUARTERS`, `QORD`, `MONTH`, `MONTHS`, `YEARS`, `COUNT`, `RATIO`, `DATE`, and `MONTHDAY`.

## Controlled-vocabulary tokens

| Token | Role | Runtime handling |
| --- | --- | --- |
| `@RECOMMENDATION` | Analyst action such as buy, hold, or sell | Explicit capture; translated through the recommendation vocabulary |
| `@CURRENCY` | Selected currency label | Explicit capture; translated through the miscellaneous vocabulary |
| `@UNIT` | Commodity or measurement unit | Explicit capture; translated through the miscellaneous vocabulary |
| `@STATE` | On/off state | Generic capture; known values are translated through the miscellaneous vocabulary |
| `@HEDGETYPE` | Hedge type | Explicit capture; translated through the miscellaneous vocabulary when known |
| `@DIRECTION` | Up/down or directional wording | Explicit capture; translated through the direction vocabulary; currently unused by the public CSV corpus |
| `@GAINLOSS` | Gain/loss result wording | Explicit capture; translated through the gain/loss vocabulary; currently unused by the public CSV corpus |
| `@VERB` | Controlled action verb | Explicit capture; translated through the verb vocabulary; currently unused by the public CSV corpus |

## Raw and legacy text tokens

| Token | Role | Runtime handling |
| --- | --- | --- |
| `@FILENAME` | Save filename | Explicit capture; preserved |
| `@PATH` | File-system path | Explicit capture; preserved |
| `@CHEATER` | Game-provided legacy narrative placeholder | Generic fallback; exact meaning varies by event |
| `@FACT` | Game-provided legacy narrative/fact fragment | Generic fallback; exact meaning varies by event |
| `@FACTG` | Game-provided legacy narrative/fact fragment | Generic fallback; exact meaning varies by event |
| `@HUMOR` | Game-provided legacy humor or narrative fragment | Generic fallback; exact meaning varies by event |
| `@LOSS` | Game-provided legacy event value | Generic fallback; exact meaning varies by event |
| `@MISC` | Miscellaneous game-provided value | Generic fallback; preserved unless the Korean template reorders or omits it |
| `@MISCAGENCY` | Miscellaneous agency name | Generic fallback; preserved |
| `@TEXT` | Arbitrary event text fragment | Generic fallback; preserved |
| `@TEXTSTRING` | Arbitrary generated text fragment | Generic fallback; preserved |

These legacy tokens should not be assigned a narrower meaning without checking the live source sentences that use them. Their safe contract is capture-and-preserve.

## Audit summary

The current public translation CSV corpus uses 52 token types:

- 37 have explicit capture patterns.
- 15 use the generic fallback: `CHEATER`, `ENTITY`, `FACT`, `FACTG`, `HUMOR`, `LOSS`, `MISC`, `MISCAGENCY`, `MOYR`, `PLAYERSHORT`, `SHARE`, `STATE`, `STEPNUM`, `TEXT`, and `TEXTSTRING`.
- Four explicit runtime patterns are defined but not currently used in the public CSV corpus: `DIRECTION`, `GAINLOSS`, `PLAYERNUM`, and `VERB`.
- Twelve token types have dedicated normalizers, listed in the numbers-and-dates section above.

Fallback tokens are not broken or discarded. They simply match less strictly, which makes an overly broad template more likely to capture unintended text. Prefer an existing explicit token for new structured values; retain a legacy fallback token when compatibility with existing game sentences is required.

## Related template syntax

`{a|b|c}`, `''`, and `{[n]a|b}` are choice syntax, not tokens:

- `{a|b|c}` matches corresponding alternative wording.
- `''` represents an empty/optional branch.
- `{[n]a|b}` reuses the nth source-side choice when Korean word order differs.

See the root [`README.md`](../README.md#template-syntax) for examples and the developer-overlay controls used to edit templates and translations.
## Multilingual extensions

The shared token inventory below is also used by non-Korean locales.
See [MULTILINGUAL.md](MULTILINGUAL.md) for `{{@TOKEN.gender|...}}`,
`.number`, `.agreement`, `.plural`, and `:FORM_*` inflections. These are
target-only extensions; English matching and existing particle/choice syntax
are unchanged. Locale registration and packaging use `locale_profiles.json`.
