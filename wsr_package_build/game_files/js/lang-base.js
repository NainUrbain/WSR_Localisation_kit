/**
 * Language rules shared by every locale, and the defaults a locale module
 * (lang-ko.js, lang-fr.js, lang-ja.js, ...) overrides.
 *
 * template-translate.js is language-neutral: it matches the English source
 * and substitutes token values into the translated template, then calls the
 * active locale's rules for everything grammar- or format-specific:
 *
 *   attach(value, { slash, modifier, record })  particle / article after a token
 *   finish(text)                   final pass over a rendered template
 *   dateToken(raw)                 @DATE capture ("1/15/2024", "January 15, 2024")
 *   formatDate(raw)                a bare date ("January 15, 2024 (Q1)")
 *   monthDay(raw)                  @MONTHDAY capture ("November 15")
 *   possessive(owner, label, body) "ACME's INDUSTRY OUTLOOK: ..." composition
 *   clause(text, kind)             adapt a lead fragment's ending when a tail
 *                                  follows: 'end' (no tail), 'contrast'
 *                                  (", but ..."), 'contrastPast'
 *   plainCountAfter                RegExp: an @AMOUNT followed by one of these
 *                                  unit words is a count, not money (no "$ ")
 *   nativeScript                   RegExp detecting text already in the
 *                                  target language (null: cannot tell)
 *   entityAliases                 leftover English entity phrases replaced
 *                                  after a successful translation
 *   memoPreamble(company)          localized long-memo heading
 *
 * To add a language: copy lang-ja.js, adjust the rules, and set runtime_module
 * and runtime_export in locale_profiles.json. The registry and dependency
 * list are generated; no engine edit is needed. See MULTILINGUAL.md.
 */

export const MONTH_NAMES = [
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
];

const MONTH_TO_NUM = {
    JANUARY: 1, FEBRUARY: 2, MARCH: 3, APRIL: 4, MAY: 5, JUNE: 6,
    JULY: 7, AUGUST: 8, SEPTEMBER: 9, OCTOBER: 10, NOVEMBER: 11, DECEMBER: 12,
    JAN: 1, FEB: 2, MAR: 3, APR: 4, JUN: 6, JUL: 7, AUG: 8,
    SEP: 9, SEPT: 9, OCT: 10, NOV: 11, DEC: 12,
};

/** "1/15/2024" or "January 15, 2024" -> {year, month, day}; null otherwise. */
export function parseDateToken(raw) {
    const v = String(raw).trim();
    const num = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(v);
    if (num) return { year: num[3], month: Number(num[1]), day: Number(num[2]) };
    const m = /^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$/.exec(v);
    if (!m) return null;
    const idx = MONTH_NAMES.indexOf(m[1].toLowerCase());
    return idx < 0 ? null : { year: m[3], month: idx + 1, day: m[2] };
}

/**
 * "January 5, 2026", "Jan 5, 2026" or with a trailing " (Q1)" tag ->
 * {year, month, day, suffix}; null when it does not parse.
 */
export function parseBareDate(raw) {
    const m = /^(\w+)\s+(\d{1,2}),\s*(\d{4})(\s*\(.*\))?$/.exec(String(raw).trim());
    if (!m) return null;
    const month = MONTH_TO_NUM[m[1].toUpperCase()];
    if (!month) return null;
    return { year: m[3], month, day: parseInt(m[2], 10), suffix: m[4] ? ' ' + m[4].trim() : '' };
}

/** "November 15" / "November 15th" -> {month, day}; null otherwise. */
export function parseMonthDay(raw) {
    const m = /^([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?$/.exec(String(raw).trim());
    if (!m) return null;
    const idx = MONTH_NAMES.indexOf(m[1].toLowerCase());
    return idx < 0 ? null : { month: idx + 1, day: m[2] };
}

export const BASE_RULES = {
    attach: (value) => value,
    finish: (text) => text,
    dateToken: (raw) => raw,
    formatDate: (raw) => raw,
    monthDay: (raw) => raw,
    month: (raw) => raw,
    possessive: (owner, label, body) => `${owner}: ${label}${body}`,
    clause: (text) => text,
    plainCountAfter: null,
    nativeScript: null,
    entityAliases: [],
    memoPreamble: (company) => `INTERNAL MEMO TO CONTROLLING SHAREHOLDER OF: ${company}\n`,
};
