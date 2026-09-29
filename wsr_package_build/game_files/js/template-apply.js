
import {
    matchTemplate,
    matchWholeBlobTemplate,
    translateReportTableRow,
    lookupExactTranslation,
    isTargetScript,
    activateLocale,
    applyLanguageAliases,
    formatMemoPreamble,
} from './template-translate.js';
import localeManager from './locale/localeManager.js';
import { resolveDebugPath } from './wsr-debug-path.js';

// template-translate.js owns loading <prefix>-templates.json for every locale.
function activateTemplateLocale(locale) {
    return activateLocale(locale);
}

const MAX_DUMP_SIZE = 100 * 1024; // ~100KB ≈ 200 JSONL lines
function appendDump(filePath, jsonLine) {
    const fsMod = (typeof require !== 'undefined') ? require('fs') : null;
    if (!fsMod || !filePath) return;
    try {
        try {
            const stat = fsMod.statSync(filePath);
            if (stat.size > MAX_DUMP_SIZE) {
                const content = fsMod.readFileSync(filePath, 'utf8');
                const lines = content.split('\n').filter(l => l.trim());
                fsMod.writeFileSync(filePath, lines.slice(-200).join('\n') + '\n', 'utf8');
            }
        } catch (_) { /* no file: skip */ }
        fsMod.appendFileSync(filePath, jsonLine + '\n');
    } catch (_) { /* diagnostics must never break the main logic */ }
}

const _lastQiDump = {};
function debugDumpQuarterlyIncomeCandidate(unit, sentences, field) {
    try {
        if (field !== 'earningsReport') return;
        const dumpPath = resolveDebugPath('debug_field_dump.jsonl');
        if (!dumpPath) return;
        const dedupKey = unit;
        if (_lastQiDump[dedupKey]) return;
        _lastQiDump[dedupKey] = true;
        const record = {
            ts: new Date().toISOString(),
            locale: localeManager.getCurrentLocale(),
            kind: 'quarterlyIncomeCandidate',
            reconstructedUnit: unit,
            splitSentences: sentences,
        };
        appendDump(dumpPath, JSON.stringify(record));
    } catch (e) {
        // never let debug tooling break the actual translation hook
    }
}

let _qiPassSeq = 0;
function debugDumpParagraphFieldPass(field, val, cachedHit) {
    try {
        const dumpPath = resolveDebugPath('debug_field_dump.jsonl');
        if (!dumpPath) return;
        const record = {
            ts: new Date().toISOString(),
            locale: localeManager.getCurrentLocale(),
            kind: 'paragraphFieldPass',
            seq: _qiPassSeq++,
            field,
            valType: Array.isArray(val) ? 'array' : typeof val,
            valPreview: Array.isArray(val)
                ? val.slice(0, 6)
                : (typeof val === 'string' ? val.slice(0, 400) : val),
            valLength: Array.isArray(val) ? val.length : (typeof val === 'string' ? val.length : null),
            cacheHit: cachedHit !== null,
        };
        appendDump(dumpPath, JSON.stringify(record));
    } catch (e) {
        // never let debug tooling break the actual translation hook
    }
}

// Fields whose array elements are fixed-width TABLE rows (industry/company
// name + numeric columns + a trend/recommendation word + optional trailing
// @I0036/@C1094-style internal reference tag) rather than prose sentences.
// A data row here will never match a sentence TEMPLATE (that's by design —
// see translateReportTableRow()'s block comment in template-translate.js),
// so translateSentence() falls back to it for exactly these fields after
// matchTemplate() reports no match. Header/footnote lines in the SAME
// fields still go through matchTemplate() first and translate normally
// (they're ordinary UI-Label-synced sentences) — this is purely a
// fallback, never a replacement.
const TABLE_ROW_FIELDS = new Set([
    'industryGrowthRatesReport', 'industryProjectionReport', 'industrySummaryReport',
    'mostCashReport', 'mostMarketCapReport', 'mostMarketShareReport', 'mostTaxLossReport',
    // whoOwnsFuturesReport is fixed-width too. Keep dotted company names such
    // as "HOLISTER OIL SERV." atomic so sentence splitting cannot collapse
    // the padding before the commodity/type column.
    'myCorporationsReport', 'whoOwnsFuturesReport', 'whoOwnsStocksReport', 'whosAheadReport',
    'whoOwnsPhysicalCommoditiesReport',
]);

const TEXT_FIELDS = [
    'newsHeadlines', 'advisorySummary', 'modalText', 'modalTitle', 'eventString', 'alerts',
    'creditInfo',
    'industryGrowthRatesReport', 'industryProjectionReport', 'industrySummaryReport',
    'mostCashReport', 'mostMarketCapReport', 'mostMarketShareReport', 'mostTaxLossReport',
    'myCorporationsReport', 'whoOwnsFuturesReport', 'whoOwnsInvestmentContractsReport',
    'whoOwnsOptionsReport', 'whoOwnsPhysicalCommoditiesReport', 'whoOwnsStocksReport',
    'whoOwnsSwapsReport', 'whosAheadReport',
    'earningsReport', 'loansReport', 'economicDataReport', 'interestRatesReport',
    'cashflowProjection', 'researchReport',
    // FinancialsTab/IndustrialView render the full company or bank detail
    // sheet from this separate gameState field.  Without it, the visible
    // report bypasses both template translation and paragraph-key metadata.
    'financialProfile',
];

const STRUCTURED_REPORT_FIELDS = new Set(
    TEXT_FIELDS.filter((f) => !['newsHeadlines', 'advisorySummary', 'modalText', 'modalTitle', 'eventString', 'alerts'].includes(f))
);

const PARAGRAPH_FIELDS = new Set([
    'researchReport', 'earningsReport', 'interestRatesReport',
    'economicDataReport', 'loansReport',
    'cashflowProjection',
    'financialProfile',
]);
const UNIT_BOUNDARY = /^(<<|\[\d+\]|\*+\s)/;

const DANGLING_END_WORDS = new Set([
    'a', 'an', 'the', 'of', 'to', 'with', 'by', 'on', 'in', 'at', 'for',
    'and', 'or', 'is', 'are', 'was', 'were', 'be', 'has', 'have', 'that', 'this',
]);
function endsWithDanglingWord(buf) {
    const m = /([A-Za-z]+)\s*$/.exec(buf);
    return !!m && DANGLING_END_WORDS.has(m[1].toLowerCase());
}
function isWrappedContinuation(trimmed, buf) {
    if (UNIT_BOUNDARY.test(trimmed)) return false;
    // A numbered quantity can continue an asterisk footnote after its colon.
    if (/^\*\s/.test(buf) && /:$/.test(buf.trim()) && /^\d[\d,]*\s/.test(trimmed)) return true;
    if (/^[a-z]/.test(trimmed)) {
        return !buf || !/[.!?]$/.test(buf.trim());
    }
    if (/^[(&]/.test(trimmed)) {
        return !buf || !/[.!?]$/.test(buf.trim());
    }
    if (/^\$/.test(trimmed)) {
        return !buf || !/[.!?]$/.test(buf.trim());
    }
    return !!buf && endsWithDanglingWord(buf);
}

function reconstructParagraphUnits(lines) {
    const units = [];
    let buf = '';
    for (const raw of lines) {
        if (typeof raw !== 'string') continue;
        const trimmed = raw.trim();
        if (!trimmed) continue;
        if (buf === '' || !isWrappedContinuation(trimmed, buf)) {
            if (buf) units.push(buf);
            buf = trimmed;
        } else if (/[a-zA-Z]-$/.test(buf)) {
            buf = buf.slice(0, -1) + trimmed;
        } else {
            buf = buf + ' ' + trimmed;
        }
    }
    if (buf) units.push(buf);
    return units;
}

let applied = 0;

const SENTENCE_ABBREVIATIONS = new Set([
    'ltd', 'co', 'cos', 'inc', 'corp', 'mr', 'mrs', 'ms', 'dr', 'st', 'jr', 'sr',
    'etc', 'vs', 'no', 'gp', 'llc', 'plc', 'intl', 'natl', 'assn',
    'govt', 'indiv', 'mkt', 'avg', 'approx', 'min', 'max', 'misc',
    'mil',
]);

const ALWAYS_ABBREV = new Set([
    'bros', 'fab', 'pers', 'prods', 'alum', 'amer', 'assoc', 'construc',
    'dept', 'elec', 'electron', 'entertain', 'equip', 'finan', 'hosp',
    'inds', 'indust', 'insur', 'pacif', 'prov', 'pubs', 'secur',
    'semicond', 'tel', 'util',
    'dot',
    'ltd', 'cos', 'inc', 'corp', 'mr', 'mrs', 'ms', 'dr', 'st', 'jr', 'sr',
    'etc', 'vs', 'no', 'gp', 'llc', 'plc', 'intl', 'assn',
    'govt', 'indiv', 'mkt', 'avg', 'approx', 'min', 'max', 'misc', 'mil',
    'oper', 'proj', 'cap', 'perform', 'avail', 'est', 'conv', 'commod',
    'vol', 'acct', 'mo',
]);

export function splitIntoSentences(text) {
    const t = (text || '').trim();
    if (!t) return [];
    const sentences = [];
    let start = 0;
    let i = 0;
    const n = t.length;
    while (i < n) {
        const ch = t[i];
        if (ch === '.' || ch === '!' || ch === '?') {
            let j = i;
            while (j + 1 < n && '.!?'.includes(t[j + 1])) j++;
            const before = t.slice(start, i);
            const wordMatch = before.match(/([A-Za-z]+)$/);
            const rawWord = wordMatch ? wordMatch[1] : '';
            const word = rawWord.toLowerCase();
            const isAllCapsTicker = rawWord.length > 1 && rawWord === rawWord.toUpperCase();
            const isAbbrev = ALWAYS_ABBREV.has(word) || (SENTENCE_ABBREVIATIONS.has(word) && !isAllCapsTicker);
            const _precedingForInitial = before.slice(0, before.length - rawWord.length);
            const isPossessiveS = word === 's' && /['’]$/.test(_precedingForInitial);
            const isInitial = word.length === 1 && word !== 'm' && !isPossessiveS;
            const isDecimal = ch === '.' && /\d$/.test(before) && /\d/.test(t[i + 1] || '');
            let k = j;
            while (k + 1 < n && ')]"\''.includes(t[k + 1])) k++;
            const afterRest = t.slice(k + 1).replace(/^\s+/, '');
            const nextChar = afterRest.length ? afterRest[0] : '';
            let endsHere = !isAbbrev && !isInitial && !isDecimal;
            const isBulletStart = /^-\s*[A-Z@]/.test(afterRest);
            if (word === 'm' && nextChar === '(') endsHere = false;
            if (endsHere && (nextChar === '' || /[A-Z("'@]/.test(nextChar) || isTargetScript(nextChar) || isBulletStart)) {
                sentences.push(t.slice(start, k + 1).trim());
                start = k + 1;
                i = k + 1;
                continue;
            }
            i = j + 1;
            continue;
        }
        i++;
    }
    const tail = t.slice(start).trim();
    if (tail) sentences.push(tail);
    return sentences.filter(Boolean);
}

function looksLikeTableDataRow(line) {
    if (line.includes('\n')) return false;
    if (/^(?:\[\d+\]|\*|\(CLICK ON)/.test(line.trim())) return false;
    const gaps = line.match(/ {2,}/g);
    return !!gaps && gaps.length >= 2;
}

const _VARIANT_RE = /\{([^{}]+)\}/g;
function resolveVariants(str) {
    if (!str || str.indexOf('{') === -1) return str;   // fast path: no braces
    return str.replace(_VARIANT_RE, (_, inner) => {
        const opts = inner.split('/');
        return opts.length > 1 ? opts[Math.floor(Math.random() * opts.length)] : inner;
    });
}

function applyEntityAliases(str) {
    return str ? applyLanguageAliases(str) : str;
}

// Translates one standalone sentence via matchTemplate(), leaving it as-is
// (English) if no template matches yet. For TABLE_ROW_FIELDS, a
// matchTemplate() miss falls through to translateReportTableRow() — a data
// row (e.g. "ADVERTISING   6%   7%  21.8%  IMPROVING   @I0036") will never
// match a sentence template, but its industry-name/trend/recommendation
// word may still be individually recognized (see that function's comment).
function translateSentence(sentence, field) {
    const locale = localeManager.getCurrentLocale();
    const hookData = typeof window !== 'undefined'
        ? window.__WSR_LOCALE_HOOK_DATA__
        : null;
    const exactHit = hookData
        ? lookupExactTranslation(sentence, hookData.exact) : null;
    if (exactHit) {
        applied++;
        return applyEntityAliases(exactHit);
    }
    if (field && TABLE_ROW_FIELDS.has(field) && looksLikeTableDataRow(sentence)) {
        const rowResult = translateReportTableRow(field, sentence);
        if (rowResult !== sentence) applied++;
        return rowResult;
    }
    const result = matchTemplate(sentence);
    if (result.matched) {
        applied++;
        // Reverse map: matchTemplate() (template-translate.js, where SOURCE_KEYS is in
        // scope) already fills __WSR_SENT_KEY__. Writing it here would store the English
        // template instead of the CSV key, so only __WSR_FIELD_KEY__ is filled here.
        if (typeof window !== 'undefined' && field) {
            if (!window.__WSR_FIELD_KEY__) window.__WSR_FIELD_KEY__ = new Map();
            window.__WSR_FIELD_KEY__.set(result.korean, field);
        }
        return applyEntityAliases(resolveVariants(result.korean));
    }
    if (field && TABLE_ROW_FIELDS.has(field)) {
        const rowResult = translateReportTableRow(field, sentence);
        if (rowResult !== sentence) applied++;
        return rowResult;
    }
    if (hookData) {
        const exactDict = hookData.exact;
        if (exactDict) {
            const t = sentence.trim();
            const hit = exactDict[t] ||
                        exactDict[t.charAt(0).toUpperCase() + t.slice(1)] ||
                        exactDict[t.charAt(0).toLowerCase() + t.slice(1)];
            if (hit && typeof hit === 'string' && hit !== t) {
                applied++;
                return applyEntityAliases(hit);
            }
        }
    }
    return sentence;
}

function realKeysForKorean(text) {
    if (typeof window === 'undefined' || !window.__WSR_SENT_KEY__) return [];
    const value = window.__WSR_SENT_KEY__.get(text);
    const values = Array.isArray(value) ? value : String(value || '').split(/\s*\|\s*/);
    return values.map((key) => key.trim()).filter((key) => key && !/\s/.test(key));
}

function rememberCombinedKeys(joinedText, translatedParts) {
    if (typeof window === 'undefined' || !window.__WSR_SENT_KEY__) return;
    const keys = [];
    for (const part of translatedParts) {
        for (const key of realKeysForKorean(part)) {
            if (!keys.includes(key)) keys.push(key);
        }
    }
    if (keys.length) window.__WSR_SENT_KEY__.set(joinedText, keys.join(' | '));
}

function rememberWholeMatchKey(translatedText, match, field) {
    if (typeof window === 'undefined' || !translatedText || !match) return;
    const key = match.key || match.source;
    if (key) {
        if (!window.__WSR_SENT_KEY__) window.__WSR_SENT_KEY__ = new Map();
        window.__WSR_SENT_KEY__.set(translatedText.trim(), key);
    }
    if (field) {
        if (!window.__WSR_FIELD_KEY__) window.__WSR_FIELD_KEY__ = new Map();
        window.__WSR_FIELD_KEY__.set(translatedText.trim(), field);
    }
}

// Splits on blank-line paragraph boundaries, KEEPING the separators (so the
// original spacing/structure can be reassembled exactly), then splits each
// paragraph into individual sentences and translates each one independently.
function translateValue(text, field) {
    if (text == null) return '';
    if (typeof text !== 'string') return text;
    const t = text.trim();
    if (!t) return text;
    const lead = text.match(/^\s*/)[0];
    const trail = text.match(/\s*$/)[0];

    const MEMO_PREAMBLE_RE = /^(INTERNAL MEMO TO CONTROLLING SHAREHOLDER OF:\s*)([^\n]+)\n/;
    const preambleMatch = t.match(MEMO_PREAMBLE_RE);
    const bodyForWholeMatch = preambleMatch ? t.slice(preambleMatch[0].length) : t;
    const wholeMatch = matchWholeBlobTemplate(bodyForWholeMatch);
    if (wholeMatch.matched) {
        applied++;
        const localizedPreamble = preambleMatch
            ? formatMemoPreamble(preambleMatch[2])
            : '';
        const translated = applyEntityAliases(resolveVariants(lead + localizedPreamble + wholeMatch.korean + trail));
        rememberWholeMatchKey(translated, wholeMatch, field);
        return translated;
    }

    if (field && TABLE_ROW_FIELDS.has(field) && looksLikeTableDataRow(t)) {
        return lead + translateSentence(t, field) + trail;
    }

    const parts = t.split(/(\r?\n\s*\r?\n)/); // odd indices are the separators
    const rebuilt = parts.map((part, idx) => {
        if (idx % 2 === 1) return part; // separator — pass through unchanged
        const wholePart = translateSentence(part, field);
        if (wholePart !== part) return wholePart;
        const sentences = splitIntoSentences(part);
        if (sentences.length === 0) return part; // e.g. a dashes-only rule line
        const _translated = sentences.map(s => translateSentence(s, field));
        // Also store the joined multi-sentence result in __WSR_SENT_KEY__, so the Phase 1
        // advisory span lookup can reverse-look-up a whole span (sentences joined by ' ').
        if (_translated.length > 1) rememberCombinedKeys(_translated.join(' '), _translated);
        return _translated.join(' ');
    });
    // Also store the whole multi-paragraph result, so FOURTH PASS can look up text containing \r\n\r\n
    // parts.length > 1 means paragraph separators were present (modal text, long descriptions, ...)
    if (parts.length > 1 && typeof window !== 'undefined' && window.__WSR_SENT_KEY__) {
        const _fullKo = rebuilt.join('');
        const _ksm2 = window.__WSR_SENT_KEY__;
        if (!_ksm2.has(_fullKo)) rememberCombinedKeys(_fullKo, rebuilt.filter((_, idx) => idx % 2 === 0));
    }
    return lead + rebuilt.join('') + trail;
}

export function translateParagraphUnit(unit, field) {
    const wholeUnit = translateSentence(unit, field);
    if (wholeUnit !== unit) return wholeUnit;
    const sentences = splitIntoSentences(unit);
    if (sentences.length === 0) return unit; // e.g. a dashes-only rule line
    debugDumpQuarterlyIncomeCandidate(unit, sentences, field);
    const _tu = sentences.map(s => translateSentence(s, field));
    if (_tu.length > 1) rememberCombinedKeys(_tu.join(' '), _tu);
    return _tu.join(' ');
}

function translateWrappedParagraphString(text, field) {
    if (typeof text !== 'string') return text;
    let t = text.trim();
    if (!t) return text;
    const lead = text.match(/^\s*/)[0];
    let trail = text.match(/\s*$/)[0];

    const endMarkerMatch = t.match(/\s*@END\s*$/);
    if (endMarkerMatch) {
        t = t.slice(0, endMarkerMatch.index).trimEnd();
        trail = endMarkerMatch[0] + trail;
    }
    if (!t) return text;

    const MEMO_PREAMBLE_RE = /^(INTERNAL MEMO TO CONTROLLING SHAREHOLDER OF:\s*)([^\n]+)\n/;
    const preambleMatch = t.match(MEMO_PREAMBLE_RE);
    const bodyForWholeMatch = preambleMatch ? t.slice(preambleMatch[0].length) : t;
    const wholeMatch = matchWholeBlobTemplate(bodyForWholeMatch);
    if (t.length > 600) {
        try {
            const dumpPath = resolveDebugPath('debug_field_dump.jsonl');
            if (dumpPath) {
                appendDump(dumpPath, JSON.stringify({
                    ts: new Date().toISOString(),
                    locale: localeManager.getCurrentLocale(),
                    kind: 'longMemoWholeBlobAttempt',
                    field,
                    rawTextLength: t.length,
                    rawText: t,
                    preambleMatched: !!preambleMatch,
                    preambleCaptured: preambleMatch ? preambleMatch[2] : null,
                    bodyForWholeMatchLength: bodyForWholeMatch.length,
                    bodyForWholeMatchPreview: bodyForWholeMatch.slice(0, 300),
                    wholeMatchResult: wholeMatch.matched,
                }));
            }
        } catch (e) { /* never let debug tooling break the actual translation hook */ }
    }
    if (wholeMatch.matched) {
        applied++;
        const localizedPreamble = preambleMatch
            ? formatMemoPreamble(preambleMatch[2])
            : '';
        const translated = applyEntityAliases(resolveVariants(lead + localizedPreamble + wholeMatch.korean + trail));
        rememberWholeMatchKey(translated, wholeMatch, field);
        return translated;
    }

    const parts = t.split(/(\r\n\s*\r\n|\r\s*\r|\n\s*\n)/); // odd indices are blank-line separators
    const rebuilt = parts.map((part, idx) => {
        if (idx % 2 === 1) return part; // separator — pass through unchanged
        const lines = part.split(/\r\n|\r|\n/);
        const units = reconstructParagraphUnits(lines);
        if (units.length === 0) return part; // e.g. a dashes-only rule line
        const partEol = (part.includes('\r') && !part.includes('\n')) ? '\r' : '\n';
        return units.map(u => translateParagraphUnit(u, field)).join(partEol);
    });
    return lead + rebuilt.join('') + trail;
}


function textDisplayWidth(str) {
    let w = 0;
    for (const ch of str) {
        const cp = ch.codePointAt(0);
        if (
            (cp >= 0x1100 && cp <= 0x11FF) ||  // Hangul Jamo
            (cp >= 0x2E80 && cp <= 0x303F) ||  // CJK Radicals / Kangxi
            (cp >= 0x3040 && cp <= 0x9FFF) ||  // Hiragana, Katakana, CJK Unified
            (cp >= 0xAC00 && cp <= 0xD7AF) ||  // Hangul Syllables (main block)
            (cp >= 0xF900 && cp <= 0xFAFF) ||  // CJK Compatibility Ideographs
            (cp >= 0xFF01 && cp <= 0xFF60) ||  // Fullwidth Latin & punctuation
            (cp >= 0xFFE0 && cp <= 0xFFE6)     // Fullwidth currency signs
        ) {
            w += 2;
        } else {
            w += 1;
        }
    }
    return w;
}

// Re-wrap `text` into an array of display lines, each no wider than
// `colWidth` columns (CJK-aware).  `headIndent` is prepended to the
// first line; `contIndent` is prepended to every continuation line.
function rewrapDenseProse(text, headIndent, contIndent, colWidth) {
    const words = text.trim().split(/\s+/);
    const lines = [];
    let curIndent = headIndent;
    let cur = '';
    let curW = 0;

    for (const word of words) {
        if (!word) continue;
        const ww = textDisplayWidth(word);
        const avail = colWidth - textDisplayWidth(curIndent);
        if (cur && curW + 1 + ww > avail) {
            lines.push(curIndent + cur);
            curIndent = contIndent;
            cur = word;
            curW = ww;
        } else {
            if (cur) { cur += ' '; curW += 1; }
            cur += word;
            curW += ww;
        }
    }
    if (cur) lines.push(curIndent + cur);
    return lines;
}

function looksLikeStructuredReport(text) {
    if ((text.match(/[\r\n]/g) || []).length < 3) return false;
    return /-{5,}/.test(text);
}

function translateLineStructuredString(text, field) {
    if (typeof text !== 'string') return text;
    const t = text.trim();
    if (!t) return text;
    const lead = text.match(/^\s*/)[0];
    const trail = text.match(/\s*$/)[0];
    const eol = (t.includes('\r') && !t.includes('\n')) ? '\r' : '\n';

    // Dense fixed-width tables (stock portfolio, ownership listings, etc.)
    // are not wrapped prose. Reconstructing paragraph units trims their
    // indentation and can merge the two header rows. Keep every physical
    // row byte-for-byte; only translate the occasional non-columnar title.
    const physicalLines = t.split(/\r\n|\r|\n/);
    const denseRows = physicalLines.filter((line) => looksLikeTableDataRow(line.trim())).length;
    if (denseRows >= 3) {
        const colWidth = Math.max(...physicalLines.map(l => l.length), 72);

        // Build groups: each group is either a passthrough (data/dash/empty) or
        // a translatable prose block that may span several physical lines.
        const groups = [];
        for (const line of physicalLines) {
            const core = line.trim();
            const isPassthrough = (
                !core ||
                looksLikeTableDataRow(core) ||
                /^\s*[-=*\s]{5,}\s*$/.test(line)
            );
            if (isPassthrough) {
                groups.push({ origLines: [line], isPassthrough: true });
                continue;
            }
            const leadSpaces = (line.match(/^ */)[0] || '').length;
            // Continuation? Deeper indent than the last prose group.
            if (groups.length > 0) {
                const prev = groups[groups.length - 1];
                if (!prev.isPassthrough && leadSpaces > prev.origLeadSpaces) {
                    prev.origLines.push(line);
                    prev.core += ' ' + core;
                    prev.contIndent = line.match(/^\s*/)[0];
                    continue;
                }
            }
            groups.push({
                origLines: [line],
                core,
                origIndent: line.match(/^\s*/)[0],
                contIndent: null,   // set when the first continuation line arrives
                origLeadSpaces: leadSpaces,
                isPassthrough: false,
            });
        }

        // Translate each group and re-wrap multi-line ones.
        const translatedLines = [];
        for (const group of groups) {
            if (group.isPassthrough) {
                translatedLines.push(...group.origLines);
                continue;
            }
            const translated = translateSentence(group.core, field);
            if (translated === group.core) {
                // No template match — emit unchanged to avoid partial garbling
                translatedLines.push(...group.origLines);
                continue;
            }
            if (group.origLines.length === 1) {
                // Single physical line: simple in-place substitution
                const orig = group.origLines[0];
                const lineTrail = orig.match(/\s*$/)[0];
                translatedLines.push(group.origIndent + translated + lineTrail);
            } else {
                // Multi-line: re-wrap with CJK-aware column width
                const ci = group.contIndent || group.origIndent;
                const rewrapped = rewrapDenseProse(translated, group.origIndent, ci, colWidth);
                translatedLines.push(...rewrapped);
            }
        }
        return lead + translatedLines.join(eol) + trail;
    }

    const parts = t.split(/(\r\n\s*\r\n|\r\s*\r|\n\s*\n)/); // odd indices are blank-line separators
    const rebuilt = parts.map((part, idx) => {
        if (idx % 2 === 1) return part; // separator — pass through unchanged, exact flavor preserved
        if (!part) return part; // blank line
        const lines = part.split(/\r\n|\r|\n/);
        const units = reconstructParagraphUnits(lines);
        if (units.length === 0) return part; // e.g. a dashes-only rule line
        return units.map(u => translateParagraphUnit(u, field)).join(eol);
    });
    return lead + rebuilt.join('') + trail;
}

const lastRawByField = new Map();
const lastResultByField = new Map();

function arraysShallowEqual(a, b) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
        if (a[i] !== b[i]) return false;
    }
    return true;
}

// Returns the cached translated result if `val` (the raw, pre-translation
// value just read from state[field]) is unchanged from last time this
// field was processed, else null.
function cachedResultFor(field, val) {
    const lastRaw = lastRawByField.get(field);
    if (lastRaw === undefined) return null;
    // WebSocket patches are applied to the already-translated UI state.
    // Unchanged fields therefore arrive as Korean (often in cloned arrays),
    // not as lastRaw. Reprocessing them also destroys the English revert stash.
    const lastResult = lastResultByField.get(field);
    if (typeof val === 'string' && val === lastResult) return lastResult;
    if (Array.isArray(val) && Array.isArray(lastResult) && arraysShallowEqual(lastResult, val)) return lastResult;
    if (Array.isArray(val) && Array.isArray(lastRaw)) {
        return arraysShallowEqual(lastRaw, val) ? lastResultByField.get(field) : null;
    }
    if (typeof val === 'string' && typeof lastRaw === 'string') {
        return lastRaw === val ? lastResultByField.get(field) : null;
    }
    return null;
}

function rememberResult(field, val, result) {
    lastRawByField.set(field, val);
    lastResultByField.set(field, result);
}

export function revertAppliedFields() {
    if (typeof window === 'undefined' || !window.__WSR_GAME_STORE__) return;
    if (lastRawByField.size === 0) return;
    const updates = {};
    for (const [field, rawVal] of lastRawByField) updates[field] = rawVal;
    window.__WSR_GAME_STORE__.setState((state) => ({
        gameState: { ...state.gameState, ...updates },
    }));
    lastRawByField.clear();
    lastResultByField.clear();
    // FIX: polling path runs requestAnimationFrame(() => setGameState(mergedKorean))
    // which can fire AFTER this revert, overwriting English back to Korean.
    // A follow-up rAF re-applies the English values and wins that race.
    requestAnimationFrame(() => {
        if (window.__WSR_TEMPLATE_APPLY__ !== false) return; // toggle is back ON — skip
        if (!window.__WSR_GAME_STORE__) return;
        window.__WSR_GAME_STORE__.setState((state) => ({
            gameState: { ...state.gameState, ...updates },
        }));
    });
}

if (typeof window !== 'undefined') {
    window.__WSR_TEMPLATE_APPLY_REFRESH__ = () => {
        revertAppliedFields();
        // Re-apply immediately with the freshly edited runtime templates.
        // Waiting for the next backend poll made overlay saves appear to do
        // nothing, especially while the game was paused in a modal.
        const store = window.__WSR_GAME_STORE__;
        if (store && typeof store.getState === 'function') {
            const current = store.getState();
            if (current && current.gameState) {
                const refreshed = { ...current.gameState };
                applyTemplatesToGameState(refreshed);
                store.setState({ ...current, gameState: refreshed });
            }
        }
        return true;
    };
}

export function applyTemplatesToGameState(state) {
    if (!state) return;
    if (typeof window !== 'undefined') window.__WSR_LAST_STATE__ = state;
    if (typeof window !== 'undefined' && window.__WSR_TEMPLATE_APPLY__ === false) return;
    const activeLocale = localeManager.getCurrentLocale();
    if (!activateTemplateLocale(activeLocale)) return;
    for (const field of TEXT_FIELDS) {
        if (PARAGRAPH_FIELDS.has(field)) continue;
        const val = state[field];
        const cached = cachedResultFor(field, val);
        if (cached !== null) { state[field] = cached; continue; }
        let result;
        if (field === 'modalText' && typeof val === 'string' && val.includes('_____')) {
            result = val;
        } else if (field === 'modalText' && typeof val === 'string' && looksLikeStructuredReport(val)) {
            result = translateLineStructuredString(val, field);
        } else if (field === 'modalText' && typeof val === 'string') {
            result = translateWrappedParagraphString(val, field);
        } else if (STRUCTURED_REPORT_FIELDS.has(field) && typeof val === 'string') {
            result = translateLineStructuredString(val, field);
        } else if (Array.isArray(val)) {
            result = val.map(v => translateValue(v, field));
        } else if (typeof val === 'string') {
            result = translateValue(val, field);
        } else {
            continue;
        }
        rememberResult(field, val, result);
        state[field] = result;
        // __WSR_PARA_MAP__: hover keys for long paragraph containers (dom-translate-hook.js paragraph scan / FOURTH PASS).
        // The first 80 characters of the translation are the fingerprint mapped to fieldName (covers every TEXT_FIELDS entry).
        if (typeof window !== 'undefined') {
            if (!window.__WSR_PARA_MAP__) window.__WSR_PARA_MAP__ = new Map();
            const _paraTextRaw = Array.isArray(result)
                ? (result.find(r => typeof r === 'string' && isTargetScript(r)) || result[0] || '')
                : (typeof result === 'string' ? result : '');
            // Some report fields contain structured row objects. The
            // paragraph fingerprint is advisory metadata only; never call
            // String.prototype methods on a row object.
            const _paraText = typeof _paraTextRaw === 'string' ? _paraTextRaw : '';
            const _paraFp = _paraText.replace(/\s+/g, ' ').trim().substring(0, 80);
            if (_paraFp.length > 10 && isTargetScript(_paraFp)) {
                window.__WSR_PARA_MAP__.set(_paraFp, field);
                const _firstLine = _paraText.split(/[\n\r]/)[0].replace(/\s+/g, ' ').trim();
                const _firstLineFp = _firstLine.substring(0, 80);
                if (_firstLineFp.length > 10 && isTargetScript(_firstLineFp) && _firstLineFp !== _paraFp) {
                    window.__WSR_PARA_MAP__.set(_firstLineFp, field);
                }
                clearTimeout(window.__WSR_TAG_TIMER__);
                window.__WSR_TAG_TIMER__ = setTimeout(function() {
                    if (typeof window.__WSR_TAG_PARAGRAPHS__ === 'function')
                        window.__WSR_TAG_PARAGRAPHS__();
                }, 200);
            }
        }
    }
    // The wrapped-line array is replaced with an array of (now-Korean)
    // complete units — fewer, longer entries instead of many short
    // wrap-width-limited ones. The renderer displays each array element as
    // its own line either way, so this is a safe 1:1 shape swap.
    for (const field of PARAGRAPH_FIELDS) {
        const val = state[field];
        const cached = cachedResultFor(field, val);
        if (cached !== null) { state[field] = cached; continue; }
        let result;
        if (Array.isArray(val)) {
            result = reconstructParagraphUnits(val).map(u => translateParagraphUnit(u, field));
        } else if (typeof val === 'string') {
            result = translateWrappedParagraphString(val, field);
        } else {
            continue;
        }
        rememberResult(field, val, result);
        state[field] = result;
        // __WSR_PARA_MAP__: hover keys for long paragraph containers (dom-translate-hook.js paragraph scan / FOURTH PASS).
        // The first 80 characters of the translation are the fingerprint mapped to fieldName (covers every TEXT_FIELDS entry).
        if (typeof window !== 'undefined') {
            if (!window.__WSR_PARA_MAP__) window.__WSR_PARA_MAP__ = new Map();
            const _paraTextRaw = Array.isArray(result)
                ? (result.find(r => typeof r === 'string' && isTargetScript(r)) || result[0] || '')
                : (typeof result === 'string' ? result : '');
            // Some report fields contain structured row objects. The
            // paragraph fingerprint is advisory metadata only; never call
            // String.prototype methods on a row object.
            const _paraText = typeof _paraTextRaw === 'string' ? _paraTextRaw : '';
            const _paraFp = _paraText.replace(/\s+/g, ' ').trim().substring(0, 80);
            if (_paraFp.length > 10 && isTargetScript(_paraFp)) {
                window.__WSR_PARA_MAP__.set(_paraFp, field);
                const _firstLine = _paraText.split(/[\n\r]/)[0].replace(/\s+/g, ' ').trim();
                const _firstLineFp = _firstLine.substring(0, 80);
                if (_firstLineFp.length > 10 && isTargetScript(_firstLineFp) && _firstLineFp !== _paraFp) {
                    window.__WSR_PARA_MAP__.set(_firstLineFp, field);
                }
                clearTimeout(window.__WSR_TAG_TIMER__);
                window.__WSR_TAG_TIMER__ = setTimeout(function() {
                    if (typeof window.__WSR_TAG_PARAGRAPHS__ === 'function')
                        window.__WSR_TAG_PARAGRAPHS__();
                }, 200);
            }
        }
    }
}

function serializeForDump(val, depth) {
    if (depth <= 0) return typeof val;
    if (Array.isArray(val)) return val.slice(0, 50).map(v => serializeForDump(v, depth - 1));
    if (val && typeof val === 'object') {
        const out = {};
        for (const k of Object.keys(val)) out[k] = serializeForDump(val[k], depth - 1);
        return out;
    }
    return val;
}
function writeDump(record) {
    try {
        const dumpPath = resolveDebugPath('wsr_dump.jsonl');
        if (!dumpPath) return false;
        appendDump(dumpPath, JSON.stringify(record));
        return dumpPath;
    } catch (e) {
        return false;
    }
}
// window.__WSR_DUMP__() with no args -> every top-level field name + its
// type/length/short preview (safe first look at a state object with
// hundreds of fields, no risk of writing a multi-MB single line).
// window.__WSR_DUMP__('fieldName') -> that field's FULL current value
// (depth-limited to 6 levels and arrays capped at 50 entries, so a runaway
// circular/huge structure can't hang the game or blow up the dump file).
// Either way, also console.log()s the same thing when DevTools happens to
// be open, and returns the record so it can be inspected directly from the
// console (`copy(__WSR_DUMP__('modalText'))` etc. work as usual).
window.__WSR_DUMP__ = function (fieldName) {
    const state = window.__WSR_LAST_STATE__;
    if (!state) {
        console.warn('[WSR_KR] no gameState captured yet -- wait for the next tick and try again');
        return null;
    }
    let record;
    if (!fieldName) {
        const fields = {};
        for (const k of Object.keys(state)) {
            const v = state[k];
            fields[k] = {
                type: Array.isArray(v) ? 'array' : typeof v,
                length: Array.isArray(v) ? v.length : (typeof v === 'string' ? v.length : undefined),
                preview: typeof v === 'string' ? v.slice(0, 120) : (Array.isArray(v) ? v.slice(0, 3) : v),
            };
        }
        record = { ts: new Date().toISOString(), kind: 'wsrDumpFieldList', fields };
    } else {
        record = { ts: new Date().toISOString(), kind: 'wsrDumpField', fieldName, value: serializeForDump(state[fieldName], 6) };
    }
    const path = writeDump(record);
    console.log('[WSR_KR] dump', fieldName || '(field list)', path ? `written to ${path}` : '(file write failed, see console only)', record);
    return record;
};
if (typeof window !== 'undefined') {
    document.addEventListener('keydown', (ev) => {
        // Ctrl+Shift+D -- dumps the full current gameState field list (not
        // one specific field, since a keyboard shortcut can't take an
        // argument) to wsr_dump.jsonl. For a SPECIFIC field's full value,
        // call window.__WSR_DUMP__('fieldName') from DevTools instead.
        if (ev.ctrlKey && ev.shiftKey && (ev.key === 'D' || ev.key === 'd')) {
            ev.preventDefault();
            window.__WSR_DUMP__();
        }
    });
    window.__WSR_TEMPLATE_APPLY__ = true;
    window.__WSR_TEMPLATE_APPLY_STATS__ = () => ({ applied });
    window.__WSR_TEMPLATE_APPLY_REVERT__ = revertAppliedFields;
}
