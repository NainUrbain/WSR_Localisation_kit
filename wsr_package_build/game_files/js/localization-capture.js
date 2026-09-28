/**
 * Korean localization — runtime string capture.
 *
 * Captures unique server-sent prose strings (news headlines, alerts, reports)
 * into a CSV file every time they pass through mergeGameState(), so that
 * playing the game repeatedly accumulates real in-game sentence instances.
 * These are used later to reconstruct "sentence recipes" (templates) by
 * diffing multiple instances of the same headline type against different
 * company names — see WSR_output_hook_feasibility.md.
 *
 * INSTALL (manual — Steam install folder is not directly writable from here):
 *   1. Copy this file to:
 *      Wall Street Raider\resources\app\js\localization-capture.js
 *   2. In Wall Street Raider\resources\app\js\api.js, add near the top
 *      (with the other imports):
 *        import { captureFromGameState } from './localization-capture.js';
 *   3. In the same file, inside `export function mergeGameState(newState) {`
 *      add as the very first line of the function body:
 *        captureFromGameState(newState);
 *   4. Relaunch the game. Every unique prose string seen will be appended to:
 *      %LOCALAPPDATA%\WSR_KR_capture\captured_strings.csv
 *      (same location on every machine, independent of where your WSR_KR
 *      repo checkout lives — copy the file into the repo when you're ready
 *      to commit it; see WSR_KR_capture_guide.md).
 *
 * Disabled automatically in native-browser / no-Node contexts (same guard
 * pattern as locale/localeManager.js). Toggle at runtime from DevTools
 * console (Ctrl+Shift+I) with:
 *   window.__WSR_CAPTURE__ = false          // pause
 *   window.__WSR_CAPTURE_STATS__()          // { uniqueCaptured, csvPath }
 *
 * NOTE: temporary dev/data-collection instrument, not part of the shipped
 * translation pipeline. Safe to remove (undo the 2 lines in api.js, delete
 * this file) once enough recipe data has been collected, or before verifying
 * game files' integrity via Steam.
 */

import { resolveCapturePath } from './wsr-capture-path.js';
import { matchTemplate } from './template-translate.js';

const _require = (typeof require !== 'undefined') ? require : null;
const fs = _require ? _require('fs') : null;
const path = _require ? _require('path') : null;
const os = _require ? _require('os') : null;

const CSV_PATH = resolveCapturePath(
    _require ? process.env.WSR_KR_CAPTURE_PATH : null, 'captured_strings.csv');

// Fields to scan. Deliberately broad — table/report fields ARE included,
// because content-level filtering (isTableRow, below) is what actually
// decides whether a given line is useful, not the field it came from. A
// field whitelist alone is brittle: newsHeadlines itself mixes real
// sentences with the occasional table-formatted line, and any *Report
// field could someday carry a genuine prose sentence buried among its
// table rows. Extend if new fields are discovered during review.
const TEXT_FIELDS = [
    'newsHeadlines',
    'alerts',
    'eventString',
    'modalTitle', // generic modal system (confirmations, prompts, etc.)
    'modalText',  // e.g. the AutoPilot on/off confirmation dialog body
    'advisorySummary', // financial-advisor summary paragraph(s)
    'creditInfo',
    // Realized Capital Losses / YTD Income Tax / UNREALIZED GAIN/LOSS ON
    // EQUITY POSITIONS / RECENT NEWS HEADLINES REGARDING @PLAYER -- stayed
    // in English despite matching Candidate Template rows already existing
    // in WSR_translation_all.csv (isolated regex tests against those exact
    // templates confirmed a match every time -- the field was simply never
    // visited): same root cause as cashflowProjection/economicDataReport
    // below -- api.js's creditInfo() calls POST /credit_info, and by the
    // same functionName<->gameState-field-name convention every OTHER
    // already-working report field here follows (mostCashReport() <->
    // 'mostCashReport', etc.), the field this panel's content lives on is
    // almost certainly literally `creditInfo`. Unconfirmed against live
    // DevTools (no screen access) -- if this guess is wrong the field is
    // simply absent from gameState and this entry is a harmless no-op,
    // same safety property every other entry here has.
    'cashflowProjection',
    'earningsReport',
    'financialProfile', // full company/bank financial detail sheet
    'economicDataReport',
    'industryGrowthRatesReport',
    'industryProjectionReport',
    'industrySummaryReport',
    'interestRatesReport',
    'loansReport',
    'mostCashReport',
    'mostMarketCapReport',
    'mostMarketShareReport',
    'mostTaxLossReport',
    'myCorporationsReport',
    'researchReport',
    'whoOwnsFuturesReport',
    'whoOwnsInvestmentContractsReport',
    'whoOwnsOptionsReport',
    'whoOwnsPhysicalCommoditiesReport',
    'whoOwnsStocksReport',
    'whoOwnsSwapsReport',
    'whosAheadReport',
];

const HANGUL_RE = /[ㄱ-ㆎ가-힣]/;

// Content-based filter: reject lines that are table/grid rows rather than
// assembled prose sentences, regardless of which field they came from.
// A row from whoOwnsStocksReport etc. is column-aligned with runs of 2+
// spaces between fields and/or ends in a @C1234 / @I0036-style internal
// reference tag; a pure rule/separator line (---, ===, ___) is likewise
// not a sentence. Real headline/report sentences (the "recipe" targets)
// don't have either shape, even when they contain a number or a $ amount.
function isTableRow(s) {
    // pure separator/rule line (dashes, underscores, equals, spaces only)
    if (/^[-=_\s]{6,}$/.test(s)) return true;
    // ends with an internal entity reference tag, e.g. "...  @C1094"
    if (/@[A-Z]\d{3,5}\s*$/.test(s)) return true;
    const gaps = s.match(/ {2,}/g);
    if (gaps && gaps.length >= 2 && /\d/.test(s)) return true;
    // Windows filesystem path containing a username (e.g. save-file dialogs)
    // — not reusable "recipe" text since the path is machine-specific.
    if (/[A-Za-z]:\\Users\\[^\\]+/.test(s)) return true;
    // bare "Label:" fragments from leaderboard/report rows (e.g. "Tycoon:",
    // a player name with nothing else) — not a translatable sentence.
    if (/^[A-Za-z][A-Za-z .]{0,20}:$/.test(s.trim())) return true;
    if (/\bDAT=/.test(s)) return true;
    if (/\(Last Played\)/.test(s)) return true;
    if (/^[A-Z][a-z]{2} '-?\d{1,2} \(no data\)$/.test(s)) return true;
    return false;
}

function isFragment(s) {
    return /^[a-z]/.test(s);
}

const PARAGRAPH_FIELDS = new Set([
    'researchReport',
    'earningsReport',
    'interestRatesReport',
    'economicDataReport',
    'loansReport',
    'cashflowProjection',
    'financialProfile',
]);
const UNIT_BOUNDARY = /^(<<|\[\d+\]|\*+\s*)/;

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
    if (/^[a-z(&$]/.test(trimmed)) {
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
            // previous line was hyphenated mid-word — join without a space,
            // dropping the hyphen (e.g. "ex-" + "traordinary" -> "extraordinary")
            buf = buf.slice(0, -1) + trimmed;
        } else {
            buf = buf + ' ' + trimmed;
        }
    }
    if (buf) units.push(buf);
    // Sentence-level splitting happens once, centrally, in captureValue()
    // below — not here — so every TEXT_FIELDS entry gets it (modalText,
    // alerts, etc. that never go through this line-reassembly step still
    // need it just as much as researchReport does).
    return units;
}

const SENTENCE_ABBREVIATIONS = new Set([
    'ltd', 'co', 'cos', 'inc', 'corp', 'mr', 'mrs', 'ms', 'dr', 'st', 'jr', 'sr',
    'etc', 'vs', 'no', 'gp', 'llc', 'plc', 'intl', 'natl', 'assn',
    'govt', 'indiv', 'mkt', 'avg', 'approx', 'min', 'max', 'misc',
    'mil',
    'bros', 'fab', 'pers', 'prods', 'alum', 'amer', 'assoc', 'construc',
    'dept', 'elec', 'electron', 'entertain', 'equip', 'finan', 'hosp',
    'inds', 'indust', 'insur', 'pacif', 'prov', 'pubs', 'secur',
    'semicond', 'tel', 'util',
]);

function splitIntoSentences(text) {
    const t = (text || '').trim();
    if (!t) return [];
    const sentences = [];
    let start = 0;
    let i = 0;
    const n = t.length;
    while (i < n) {
        const ch = t[i];
        if (ch === '.' || ch === '!' || ch === '?') {
            // extend over a run of terminal punctuation, e.g. "..", "?!"
            let j = i;
            while (j + 1 < n && '.!?'.includes(t[j + 1])) j++;
            const before = t.slice(start, i);
            const wordMatch = before.match(/([A-Za-z]+)$/);
            const word = wordMatch ? wordMatch[1].toLowerCase() : '';
            const _rawWordCap = wordMatch ? wordMatch[1] : '';
            const isAbbrev = SENTENCE_ABBREVIATIONS.has(word);
            const _precedingForInitialCap = before.slice(0, before.length - _rawWordCap.length);
            const isPossessiveS = word === 's' && /['']$/.test(_precedingForInitialCap);
            const isInitial = word.length === 1 && !isPossessiveS;
            const isDecimal = ch === '.' && /\d$/.test(before);
            // A parenthetical/quoted aside often ends together with the
            // sentence punctuation, e.g. "...yourself.)" — the real "next
            // sentence" check has to look past that trailing closer, not
            // right at it, or "(...)\n\nDO YOU REALLY WANT...?" never splits.
            let k = j;
            while (k + 1 < n && ')]"\''.includes(t[k + 1])) k++;
            const afterRest = t.slice(k + 1).replace(/^\s+/, '');
            const nextChar = afterRest.length ? afterRest[0] : '';
            const endsHere = !isAbbrev && !isInitial && !isDecimal;
            if (endsHere && (nextChar === '' || /[A-Z("']/.test(nextChar))) {
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

// Table/report rows (prices, ratios, % ownership, etc.) reprint the exact
// same row with only the numbers changed on every poll — those aren't
// useful "recipe" variety, just churn that would otherwise bloat the CSV
// forever. We dedupe on a NUMBER-MASKED shape in addition to the exact
// text: once a row's shape (all digit runs, %, and @C1234-style refs
// replaced with '#') has been seen, later re-prints that only differ by
// digits are skipped, while a row that's genuinely new (different company
// name, different industry, new headline wording) still gets through.
function normalizeShape(s) {
    return s.replace(/-?\d[\d,]*\.?\d*%?/g, '#');
}

const seen = new Set();
const seenShape = new Set();
// Reference-identity cache: mergeGameState() reuses the previous reference
// for any array/string field whose contents didn't change (see its BUG-105
// comment in api.js). We piggyback on that — if a field's reference is the
// same object as last time we looked at it, its contents can't have new
// text in them, so skip re-walking it entirely. This avoids re-scanning
// large unchanged report arrays on every ~10Hz patch tick.
const lastRef = new Map();
let ready = false;
let enabled = !!(fs && CSV_PATH);

// Pending rows are buffered and flushed asynchronously on an interval,
// instead of writing synchronously (fs.appendFileSync) on every new string.
// Sync file I/O on the renderer's single thread would briefly block
// rendering; batching + fs.appendFile (async) avoids any stutter even
// during bursts of many new headlines at once.
let pending = [];
let flushTimer = null;
const FLUSH_INTERVAL_MS = 3000;

function csvEscape(s) {
    const needsQuote = /[",\n\r]/.test(s);
    const out = s.replace(/"/g, '""');
    return needsQuote ? `"${out}"` : out;
}

function ensureReady() {
    if (ready || !fs) return;
    ready = true;
    try {
        const dir = path.dirname(CSV_PATH);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        if (!fs.existsSync(CSV_PATH)) {
            fs.writeFileSync(CSV_PATH, 'captured_at,field,text\n', 'utf8');
            return;
        }
        // Seed `seen` from existing rows so relaunching the game across many
        // play sessions accumulates instead of re-writing duplicates.
        const content = fs.readFileSync(CSV_PATH, 'utf8');
        const lines = content.split(/\r?\n/).slice(1);
        for (const line of lines) {
            if (!line) continue;
            const m = line.match(/^[^,]*,[^,]*,(.*)$/s);
            if (!m) continue;
            let text = m[1];
            if (text.startsWith('"') && text.endsWith('"')) {
                text = text.slice(1, -1).replace(/""/g, '"');
            }
            seen.add(text);
            seenShape.add(normalizeShape(text));
        }
        console.log(`[localization-capture] loaded ${seen.size} previously captured strings`);
    } catch (e) {
        console.error('[localization-capture] init failed:', e);
    }
}

function queueRow(field, text) {
    pending.push(`${new Date().toISOString()},${csvEscape(field)},${csvEscape(text)}\n`);
    if (!flushTimer) {
        flushTimer = setTimeout(flushPending, FLUSH_INTERVAL_MS);
    }
}

function flushPending() {
    flushTimer = null;
    if (pending.length === 0) return;
    const batch = pending;
    pending = [];
    fs.appendFile(CSV_PATH, batch.join(''), 'utf8', (e) => {
        if (e) console.error('[localization-capture] write failed:', e);
    });
}

function finalizeCapture(field, t) {
    if (t.length < 4 || seen.has(t)) return;
    if (HANGUL_RE.test(t)) { seen.add(t); return; }
    try {
        const _m = matchTemplate(t);
        if (_m.matched && _m.korean.trim() !== t.trim()) { seen.add(t); return; }
    } catch (e) { /* matcher must never break capture */ }
    if (isTableRow(t) || isFragment(t)) { seen.add(t); return; }
    const shape = normalizeShape(t);
    if (seenShape.has(shape)) {
        // Same row shape already captured — only numbers/refs differ
        // (e.g. a price tick or % updated). Not new "recipe" info.
        seen.add(t);
        return;
    }
    seen.add(t);
    seenShape.add(shape);
    queueRow(field, t);
}

function captureValue(field, value) {
    if (typeof value === 'string') {
        const raw = value.trim();
        if (!raw) return;
        if (isTableRow(raw)) { seen.add(raw); return; }
        // Split BEFORE any of the filters below — a glued 2-sentence string
        // could otherwise get skipped/deduped as a whole unit instead of
        // being evaluated one sentence at a time (e.g. a modalText dialog
        // that has one already-seen sentence and one brand new sentence
        // glued together must still capture the new one).
        const sentences = splitIntoSentences(raw);
        if (sentences.length > 1) {
            for (const s of sentences) captureValue(field, s);
            return;
        }
        const t = sentences.length === 1 ? sentences[0] : raw;
        finalizeCapture(field, t);
    } else if (Array.isArray(value)) {
        for (const v of value) captureValue(field, v);
    } else if (value && typeof value === 'object') {
        for (const k of Object.keys(value)) captureValue(`${field}.${k}`, value[k]);
    }
}

const HOLD_MS = 1500;
const pendingLastUnit = new Map(); // field -> { text, timer }

function captureParagraphUnits(field, units) {
    if (units.length === 0) return;
    for (let i = 0; i < units.length - 1; i++) {
        captureValue(field, units[i]);
    }
    const last = units[units.length - 1];
    const pending = pendingLastUnit.get(field);
    if (pending && last !== pending.text && last.startsWith(pending.text)) {
        // Grew since last tick — still the same in-progress unit, just
        // longer now. Keep holding (reset the timer below).
        clearTimeout(pending.timer);
    } else if (pending && last !== pending.text) {
        // A different, unrelated final unit showed up — the held one is
        // as complete as it's ever going to get. Capture it as-is rather
        // than lose it silently.
        clearTimeout(pending.timer);
        captureValue(field, pending.text);
    } else if (pending) {
        // last === pending.text — no change, just refresh the timer.
        clearTimeout(pending.timer);
    }
    const timer = setTimeout(() => {
        pendingLastUnit.delete(field);
        captureValue(field, last);
    }, HOLD_MS);
    pendingLastUnit.set(field, { text: last, timer });
}

export function captureFromGameState(state) {
    if (!enabled || !state) return;
    if (typeof window !== 'undefined' && window.__WSR_CAPTURE__ === false) return;
    ensureReady();
    for (const field of TEXT_FIELDS) {
        if (!(field in state)) continue;
        const value = state[field];
        // Skip fields whose reference is unchanged since last call — their
        // contents can't contain anything new (see lastRef comment above).
        if (lastRef.get(field) === value) continue;
        lastRef.set(field, value);
        if (PARAGRAPH_FIELDS.has(field) && Array.isArray(value)) {
            captureParagraphUnits(field, reconstructParagraphUnits(value));
        } else {
            captureValue(field, value);
        }
    }
}

// Flush on shutdown so the last few seconds of a session aren't lost —
// including any still-growing last unit that never got a chance to finish
// before the game closed.
function flushAll() {
    for (const [field, pending] of pendingLastUnit) {
        clearTimeout(pending.timer);
        captureValue(field, pending.text);
    }
    pendingLastUnit.clear();
    flushPending();
}
if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', flushAll);
}

if (typeof window !== 'undefined') {
    window.__WSR_CAPTURE__ = enabled;
    window.__WSR_CAPTURE_STATS__ = () => ({
        uniqueCaptured: seen.size,
        uniqueShapes: seenShape.size,
        pendingWrite: pending.length,
        csvPath: CSV_PATH,
    });
}
