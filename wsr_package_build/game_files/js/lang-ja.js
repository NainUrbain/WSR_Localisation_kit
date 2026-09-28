/**
 * Japanese (ja-JP) language rules — see lang-base.js for the interface.
 *
 * Japanese particles (は/が/を/の …) do not change with the preceding word,
 * so templates write them directly after a token (`@CORPは`) and no
 * particle logic is needed. This is the smallest complete language module;
 * copy it as the starting point for a new language.
 */
import { BASE_RULES, MONTH_NAMES, parseDateToken, parseBareDate, parseMonthDay } from './lang-base.js';

export const JA_RULES = {
    ...BASE_RULES,
    month: (raw) => String(MONTH_NAMES.indexOf(raw.trim().toLowerCase()) + 1 || raw),
    dateToken(raw) {
        const d = parseDateToken(raw);
        return d ? `${d.year}年${d.month}月${d.day}日` : raw;
    },
    formatDate(raw) {
        const d = parseBareDate(raw);
        return d ? `${d.year}年${d.month}月${d.day}日${d.suffix}` : raw;
    },
    monthDay(raw) {
        const d = parseMonthDay(raw);
        return d ? `${d.month}月${d.day}日` : raw;
    },
    possessive: (owner, label, body) => `${owner}の${label}${body}`,
    plainCountAfter: /^\s?(コイン|個|ポイント|単位)/,
    nativeScript: /[぀-ヿ㐀-鿿]/,
    entityAliases: [
        [/\bThe company\b/g, '当該企業'],
        [/\bthe company\b/g, '当該企業'],
    ],
    memoPreamble: (company) => `支配株主向け社内メモ（対象企業：${company}）\n`,
};
