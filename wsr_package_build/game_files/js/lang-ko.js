/**
 * Korean (ko-KR) language rules — see lang-base.js for the interface.
 *
 * Particles: a template may write the slash pair a translator types in a
 * spreadsheet right after a token (`@CORP은/는`, `@CORP이/가`, `@CORP을/를`,
 * `@CORP과/와`, `@CORP이나/나`, `@CORP로/으로` or `@CORP(으)로`), or the
 * older colon form (`@CORP:TOPIC`, `:SUBJECT`, `:OBJECT`, `:AND`,
 * `:ALSO_EVEN`, `:RO`). The correct half is chosen from the actual value's
 * final consonant via attachJosa.js. A pair left after any other word is
 * resolved by finish().
 */
import { attachJosa, attachRo, pickJosa, JOSA } from './attachJosa.js';
import { BASE_RULES, MONTH_NAMES, parseDateToken, parseBareDate, parseMonthDay } from './lang-base.js';

// Longer alternatives (이나/나) must come before shorter ones.
const SLASH_JOSA_MAP = {
    '은/는': JOSA.TOPIC,
    '이/가': JOSA.SUBJECT,
    '을/를': JOSA.OBJECT,
    '과/와': JOSA.AND,
    '이나/나': JOSA.ALSO_EVEN,
};
const RO_NOTATIONS = new Set(['로/으로', '으로/로', '(으)로']);
const LOOSE_JOSA_RE = /(M\.|[가-힣A-Za-z0-9\)\]])(은\/는|이\/가|을\/를|과\/와|이나\/나)/g;

export const KO_RULES = {
    ...BASE_RULES,
    month: (raw) => String(MONTH_NAMES.indexOf(raw.trim().toLowerCase()) + 1 || raw),
    // Regex alternation of notations written directly after a token.
    notations: '은\\/는|이나\\/나|이\\/가|을\\/를|과\\/와|로\\/으로|으로\\/로|\\(으\\)로',
    attach(value, { slash, modifier }) {
        if (slash) {
            if (RO_NOTATIONS.has(slash)) return attachRo(value);
            if (SLASH_JOSA_MAP[slash]) return attachJosa(value, SLASH_JOSA_MAP[slash]);
            return value;
        }
        if (modifier) {
            if (modifier === 'RO') return attachRo(value);
            if (JOSA[modifier]) return attachJosa(value, JOSA[modifier]);
        }
        return value;
    },
    finish(text) {
        return text.replace(LOOSE_JOSA_RE, (whole, prev, pair) => {
            const word = prev === 'M.' ? '밀리언' : prev;
            return prev + pickJosa(word, SLASH_JOSA_MAP[pair]);
        });
    },
    dateToken(raw) {
        const d = parseDateToken(raw);
        return d ? `${d.year}년 ${d.month}월 ${d.day}일` : raw;
    },
    formatDate(raw) {
        const d = parseBareDate(raw);
        return d ? `${d.year}년 ${d.month}월 ${d.day}일${d.suffix}` : raw;
    },
    monthDay(raw) {
        const d = parseMonthDay(raw);
        return d ? `${d.month}월 ${d.day}일` : raw;
    },
    possessive: (owner, label, body) => `${owner}의 ${label}${body}`,
    clause(text, kind) {
        if (kind === 'end') return text.replace(/이며,$/, '입니다.');
        if (kind === 'contrast') return text.replace(/이며,$/, '이지만,');
        if (kind === 'contrastPast') return text.replace(/했습니다\.$/, '했으나,');
        return text;
    },
    plainCountAfter: /^\s?(코인|개|포인트|단위)/,
    nativeScript: /[가-힣]/,
    entityAliases: [
        [/\bThe company\b/g, '해당 기업'],
        [/\bthe company\b/g, '해당 기업'],
    ],
    memoPreamble: (company) => `지배 주주님께 드리는 내부 메모 (대상 기업: ${company})\n`,
};
