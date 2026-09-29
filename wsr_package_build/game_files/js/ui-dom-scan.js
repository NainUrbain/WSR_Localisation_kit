
import { jaJP } from './locale/ja-JP.js';
import { matchTemplate } from './template-translate.js';
import { resolveCapturePath } from './wsr-capture-path.js';

const _require = (typeof require !== 'undefined') ? require : null;
const fs = _require ? _require('fs') : null;
const path = _require ? _require('path') : null;
const os = _require ? _require('os') : null;

// Korean text in the DOM means the translation hooks already replaced it —
// capturing it back is pure noise (and used to require a Korean-text skip
// filter in the OFFLINE pipeline instead; filtering at the source is
// cheaper for everyone).
const HANGUL_RE = /[ㄱ-ㆎ가-힣]/;

// True when the Korean layer already knows how to handle this exact text:
// either it contains Hangul (already translated in-DOM), or a translated
// @TOKEN template fully matches it (template-translate.js's own matcher —
// TEMPLATES only holds rows whose translation is done, so an English
// sentence matching one is already-translated material, not new work).
function alreadyCovered(t) {
    if (HANGUL_RE.test(t)) return true;
    try {
        if (matchTemplate(t).matched) return true;
    } catch (e) { /* matcher must never break capture */ }
    return false;
}

let CAPTURE_EXCLUSIONS = { tickers: [], companyNames: [], industries: [] };
if (fs && path) {
    const exclusionCandidates = [
        path.join(__dirname, 'locale', 'wsr-capture-exclusions.json'),
        path.join(__dirname, 'js', 'locale', 'wsr-capture-exclusions.json'),
        path.join(__dirname, '..', 'locale', 'wsr-capture-exclusions.json'),
        path.join(__dirname, '..', 'js', 'locale', 'wsr-capture-exclusions.json'),
    ];
    for (const p of exclusionCandidates) {
        try {
            if (!fs.existsSync(p)) continue;
            CAPTURE_EXCLUSIONS = JSON.parse(fs.readFileSync(p, 'utf8'));
            console.log(`[ui-dom-scan] loaded wsr-capture-exclusions.json from ${p}`);
            break;
        } catch (e) {
            console.error('[ui-dom-scan] failed to load wsr-capture-exclusions.json:', e);
        }
    }
}
const EXCLUDED_TICKERS = new Set(CAPTURE_EXCLUSIONS.tickers || []);
const EXCLUDED_COMPANY_NAMES = new Set(CAPTURE_EXCLUSIONS.companyNames || []);
const EXCLUDED_INDUSTRIES = new Set(CAPTURE_EXCLUSIONS.industries || []);
const AMOUNT_SHAPED_RE = /^-?\$?\s?-?[\d,]+(\.\d+)?\s?(([BMK])|billion|million|thousand)?$/i;
const NAVIGATE_TO_RE = /^Navigate to /;
const CEO_OF_RE = /^CEO of /;
// Stock-screener/quote-list row ("PAMPAS PETROLEUM 135 %_C BBB 23.3 5.8%
// 0.7% HOLD") — a whole per-instance table row rendered as one text node
// (single spaces, so isTableRow()'s 2+-space-gap check doesn't catch it).
// Distinctive enough signature (ends in a recommendation word AND has a %
// sign AND has a digit) that it won't collide with real static UI text.
const QUOTE_ROW_RE = /%.*\d.*\b(STRONG BUY|STRONG SELL|BUY|SELL|HOLD|NOT TRADED)$/;
// "EXMONT-GLOBAL CORPORATION (XG)" / "FINANCIAL SHARES FUND (FINF)" —
// company full name (or ticker) with the other in parens, a format the
// plain exact-match check above misses since the combined string isn't
// itself a key in either list.
const NAME_PAREN_TICKER_RE = /^(.+) \(([A-Z]{1,6})\)$/;
const ENTITY_PLACEHOLDER_RE = /^Entity #\d+$/;
const STRAY_CLOSING_PUNCT_RE = /^[)\]]/;

let KNOWN_LABELS = [];
if (fs && path) {
    const hookDataCandidates = [
        path.join(__dirname, 'locale', 'ko-hook-data.json'),
        path.join(__dirname, 'js', 'locale', 'ko-hook-data.json'),
        path.join(__dirname, '..', 'locale', 'ko-hook-data.json'),
        path.join(__dirname, '..', 'js', 'locale', 'ko-hook-data.json'),
    ];
    for (const p of hookDataCandidates) {
        try {
            if (!fs.existsSync(p)) continue;
            const data = JSON.parse(fs.readFileSync(p, 'utf8'));
            KNOWN_LABELS = Object.keys(data.labels || {});
            console.log(`[ui-dom-scan] loaded ${KNOWN_LABELS.length} known label(s) from ${p}`);
            break;
        } catch (e) {
            console.error('[ui-dom-scan] failed to load ko-hook-data.json:', e);
        }
    }
}
// Longest-prefix-first so e.g. "Net Worth:" isn't shadowed by a shorter
// unrelated label that also happens to prefix-match.
const KNOWN_LABELS_SORTED = KNOWN_LABELS.slice().sort((a, b) => b.length - a.length);
const LIVE_VALUE_TAIL_RE = /^:?\s+-?\$?[\d,]+(\.\d+)?%?\.?$/;
function isKnownLabelWithLiveValue(t) {
    for (const label of KNOWN_LABELS_SORTED) {
        if (t.startsWith(label) && LIVE_VALUE_TAIL_RE.test(t.slice(label.length))) return true;
    }
    return false;
}

function isKnownEntityValue(t) {
    if (AMOUNT_SHAPED_RE.test(t) || NAVIGATE_TO_RE.test(t) || CEO_OF_RE.test(t) || QUOTE_ROW_RE.test(t)) return true;
    if (ENTITY_PLACEHOLDER_RE.test(t) || STRAY_CLOSING_PUNCT_RE.test(t)) return true;
    if (isKnownLabelWithLiveValue(t)) return true;
    const upper = t.toUpperCase();
    if (EXCLUDED_TICKERS.has(upper) || EXCLUDED_COMPANY_NAMES.has(upper) || EXCLUDED_INDUSTRIES.has(upper)) return true;
    const m = NAME_PAREN_TICKER_RE.exec(t);
    if (m && (EXCLUDED_COMPANY_NAMES.has(m[1].toUpperCase()) || EXCLUDED_TICKERS.has(m[2].toUpperCase()))) return true;
    return false;
}

const CSV_PATH = resolveCapturePath(
    _require ? process.env.WSR_KR_CAPTURE_PATH_UI : null, 'confirmed_ui_labels.csv');

// New-candidate log (see file header, "THIRD PROBLEM") — static UI text
// that renders as a complete element but ISN'T in the ja-JP master
// dictionary at all, so the pass above would otherwise just discard it.
const CSV_PATH_NEW = resolveCapturePath(
    _require ? process.env.WSR_KR_CAPTURE_PATH_UI_NEW : null, 'static_ui_candidates.csv');

const DICT_KEYS = new Set(Object.keys(jaJP || {}).map(k => k.trim()).filter(Boolean));

const scannedTexts = new Set();      // every distinct trimmed text node seen (for stats only)
const confirmed = new Set();         // trimmed texts confirmed to match a dictionary key
const sentenceSeen = new Set();      // full mixed-content sentences already captured (dedup only)
const newCandidateSeen = new Set();  // trimmed texts already logged to static_ui_candidates.csv

const NOISE_CLASSES = new Set([
    'num',
    'fixed-width cursor-pointer text-blue-400 hover:bg-blue-700 rounded px-1',
    'news-headline',
]);

// Ported from localization-capture.js (kept in sync by hand) — a leaf UI
// element's full text is never a table/grid row, but IS sometimes the
// lowercase-starting tail of a longer label that got split across
// elements, which is useless on its own the same way a mid-sentence
// gameState fragment is.
function isFragment(s) {
    return /^[a-z]/.test(s);
}

const DOLLAR_MONEY_RE = /^\$\s?-?[\d,]+(\.\d+)?\s*(billion|million|M|k)?\.?\$?$/i;
const MONEY_RATING_RE = /^[\d,]+(\.\d+)?\s*M\.?(\s*_?C?)?(\s*\*?\s*[A-Z]{1,4}\*?)?\s*$/;
const PERCENT_ONLY_RE = /^-?[\d,]+(\.\d+)?\s*%(_C)?$/;
const RATING_ONLY_RE = /^\*?\s*[A-Z]{1,4}\*?$/;
const NA_ONLY_RE = /^N\/A\s*\*?$/;
const MULTIPLE_RE = /^-?\d+(\.\d+)?x$/i;
const FULL_DATE_RE = /^[A-Z][a-z]+ \d{1,2}, \d{4}$/;
const TICKER_NAME_RE = /^[A-Z0-9.]{1,8} - [A-Z0-9 .,&'-]+$/;
const BOND_NAME_RE = /^[A-Za-z0-9 .-]+ \d+(\.\d+)?% due \d{4}$/;
const CRYPTO_PRICE_RE = /(Bitcoin|Ethereum):/;
const K_VALUE_RE = /^-?[\d,]+(\.\d+)?k\$?$/i;
const QUARTER_AXIS_RE = /^[A-Z][a-z]{2}\s*'-?\d+$/;              // "Dec '26", chart x-axis tick
const NAME_NUM_ROW_RE = /^[A-Z][A-Za-z0-9 &.,'/-]+ -?[\d,]+(\.\d+)?(\s+-?[\d,]+(\.\d+)?%?){2,}$/; // "TYCOON 314 2286 2600 -1318 1316"
const DYNAMIC_VALUE_RES = [
    DOLLAR_MONEY_RE, MONEY_RATING_RE, PERCENT_ONLY_RE, RATING_ONLY_RE, NA_ONLY_RE,
    MULTIPLE_RE, FULL_DATE_RE, TICKER_NAME_RE, BOND_NAME_RE, K_VALUE_RE,
    QUARTER_AXIS_RE, NAME_NUM_ROW_RE,
];
// Reuses endsWithDanglingWord()/DANGLING_END_WORDS defined further below
// (function declarations are hoisted, so calling it here before its
// textual definition is safe -- both are only ever actually invoked once
// scanning starts, well after the whole module has finished loading) --
// same list used there for isWrappedContinuation's wrap-detection, reused
// here for the opposite direction: a candidate whose text ENDS on one of
// these words is almost always a lead fragment cut off right before an
// inline company/industry link, not real content.
function isDynamicReportValue(t) {
    if (DYNAMIC_VALUE_RES.some((re) => re.test(t))) return true;
    if (CRYPTO_PRICE_RE.test(t)) return true;
    if (/^[a-z(&']/.test(t)) return true; // link-split TAIL fragment (isFragment only catches lowercase-start)
    if (endsWithDanglingWord(t)) return true; // link-split LEAD fragment
    return false;
}
function isTableRow(s) {
    if (/^[-=_\s]{6,}$/.test(s)) return true;
    const gaps = s.match(/ {2,}/g);
    if (gaps && gaps.length >= 2 && /\d/.test(s)) return true;
    if (/^[A-Za-z][A-Za-z .]{0,20}:$/.test(s.trim())) return true;
    return false;
}

// Inline elements that commonly wrap a variable (company name, ticker link,
// bold/italic emphasis) INSIDE a sentence, as opposed to block containers
// (div/li/p/td) that hold a whole sentence/paragraph of their own. Only
// treat an element as a "sentence container" if its element children are
// all inline-ish — otherwise we'd walk all the way up to <body> and capture
// the entire page as one "sentence".
const INLINE_TAGS = new Set(['a','span','b','i','em','strong','u','small','sub','sup','mark']);

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
    if (/^[a-z(&]/.test(trimmed)) return true;
    return !!buf && endsWithDanglingWord(buf);
}
function isAdjacentWrappedLine(prevEl, curEl) {
    if (!prevEl || !curEl || prevEl === curEl) return false;
    if (prevEl.parentElement !== curEl.parentElement) return false;
    return prevEl.nextElementSibling === curEl;
}

let pending = [];
let pendingNew = [];
let flushTimer = null;
const FLUSH_INTERVAL_MS = 3000;
let enabled = !!(fs && CSV_PATH && typeof document !== 'undefined');
let ready = false;

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
            fs.writeFileSync(CSV_PATH, 'confirmed_at,element_tag,text\n', 'utf8');
        } else {
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
                confirmed.add(text);
            }
            console.log(`[ui-dom-scan] loaded ${confirmed.size} previously confirmed UI labels`);
        }

        if (CSV_PATH_NEW) {
            if (!fs.existsSync(CSV_PATH_NEW)) {
                fs.writeFileSync(CSV_PATH_NEW, 'captured_at,element_tag,element_class,data_testid,text\n', 'utf8');
            } else {
                const content = fs.readFileSync(CSV_PATH_NEW, 'utf8');
                const lines = content.split(/\r?\n/).slice(1);
                for (const line of lines) {
                    if (!line) continue;
                    // last column (text) may itself contain quoted commas —
                    // same trailing-field trick as the confirmed-labels parser.
                    const m = line.match(/^[^,]*,[^,]*,[^,]*,[^,]*,(.*)$/s);
                    if (!m) continue;
                    let text = m[1];
                    if (text.startsWith('"') && text.endsWith('"')) {
                        text = text.slice(1, -1).replace(/""/g, '"');
                    }
                    newCandidateSeen.add(text);
                }
                console.log(`[ui-dom-scan] loaded ${newCandidateSeen.size} previously logged new-candidate UI texts`);
            }
        }
    } catch (e) {
        console.error('[ui-dom-scan] init failed:', e);
    }
}

function queueRow(tag, text) {
    pending.push(`${new Date().toISOString()},${csvEscape(tag)},${csvEscape(text)}\n`);
    if (!flushTimer) flushTimer = setTimeout(flushPending, FLUSH_INTERVAL_MS);
}

function queueNewCandidateRow(tag, cls, testid, text) {
    if (!CSV_PATH_NEW) return;
    pendingNew.push(`${new Date().toISOString()},${csvEscape(tag)},${csvEscape(cls || '')},${csvEscape(testid || '')},${csvEscape(text)}\n`);
    if (!flushTimer) flushTimer = setTimeout(flushPending, FLUSH_INTERVAL_MS);
}

function flushPending() {
    flushTimer = null;
    if (pending.length > 0) {
        const batch = pending;
        pending = [];
        fs.appendFile(CSV_PATH, batch.join(''), 'utf8', (e) => {
            if (e) console.error('[ui-dom-scan] write failed:', e);
        });
    }
    if (pendingNew.length > 0 && CSV_PATH_NEW) {
        const batchNew = pendingNew;
        pendingNew = [];
        fs.appendFile(CSV_PATH_NEW, batchNew.join(''), 'utf8', (e) => {
            if (e) console.error('[ui-dom-scan] new-candidate write failed:', e);
        });
    }
}

// data-testid is the most reliable "where did this come from" hint we get
// for free (see the Tutorials modal cards, each carrying
// data-testid="tutorial-card-tutorial-01-first-trade" etc.) — walk up from
// the text node's parent a few levels since the testid is often on an
// ancestor (the card <button>), not the leaf text div itself.
function nearestTestId(el) {
    let node = el;
    for (let i = 0; node && i < 4; i++, node = node.parentElement) {
        const id = node.getAttribute && node.getAttribute('data-testid');
        if (id) return id;
    }
    return '';
}

function considerText(text, el, tagOverride) {
    const t = (text || '').replace(/\s+/g, ' ').trim();
    if (!t) return;
    if (scannedTexts.has(t)) return;
    scannedTexts.add(t);
    const tag = tagOverride || (el ? el.tagName.toLowerCase() : 'text');
    if (DICT_KEYS.has(t)) {
        if (t.length <= 120 && !confirmed.has(t) && !isFragment(t) && !isTableRow(t)) {
            ensureReady();
            confirmed.add(t);
            queueRow(tag, t);
        }
        return;
    }
    // Not a known dictionary key — see file header, "THIRD PROBLEM". Log it
    // as a new candidate instead of silently dropping it, filtered the same
    // way gameState text is (fragment/table-row), with a wider length cap
    // since some of these are full paragraph-length tutorial copy.
    if (t.length < 4 || t.length > 400) return;
    if (!/[A-Za-z]/.test(t)) return;
    if (isFragment(t) || isTableRow(t)) return;
    if (isDynamicReportValue(t)) return;
    const cls = (el && el.className && typeof el.className === 'string') ? el.className : '';
    if (tag === 'li' && cls === '') return;
    if (alreadyCovered(t)) return;
    if (isKnownEntityValue(t)) return;
    ensureReady();
    if (newCandidateSeen.has(t)) return;
    newCandidateSeen.add(t);
    queueNewCandidateRow(tag, cls, el ? nearestTestId(el) : '', t);
}

function hasMixedInlineContent(el) {
    let hasText = false;
    let hasInlineElement = false;
    let hasBlockElement = false;
    for (const child of el.childNodes) {
        if (child.nodeType === 3 && child.nodeValue && child.nodeValue.trim()) {
            hasText = true;
        } else if (child.nodeType === 1) {
            if (INLINE_TAGS.has(child.tagName.toLowerCase())) hasInlineElement = true;
            else hasBlockElement = true;
        }
    }
    return hasText && hasInlineElement && !hasBlockElement;
}

function considerSentence(el) {
    const t = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (t.length < 8 || t.length > 300) return; // not a sentence fragment / too long to be one unit
    if (sentenceSeen.has(t)) return;
    sentenceSeen.add(t);
    if (alreadyCovered(t)) return;
    ensureReady();
    queueRow(el.tagName.toLowerCase() + '[sentence]', t);
}

function* scanNodeSteps(root) {
    if (!root || root.nodeType === undefined) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    let node;
    let bufText = '';
    let bufEl = null;
    const flush = () => {
        if (bufText) considerText(bufText, bufEl);
        bufText = '';
        bufEl = null;
    };
    while ((node = walker.nextNode())) {
        yield;
        if (!node.isConnected) continue;
        const parentEl = node.parentElement;
        const trimmed = (node.nodeValue || '').replace(/\s+/g, ' ').trim();
        if (bufText && trimmed && isAdjacentWrappedLine(bufEl, parentEl) &&
            isWrappedContinuation(trimmed, bufText)) {
            bufText = /[a-zA-Z]-$/.test(bufText) ? bufText.slice(0, -1) + trimmed : bufText + ' ' + trimmed;
            continue;
        }
        flush();
        bufText = trimmed;
        bufEl = parentEl;
    }
    flush();
    // Also check common attribute-based labels that aren't text nodes:
    // title=, aria-label=, placeholder=, value= (for <option>/<button type=button value=>).
    if (root.querySelectorAll) {
        for (const el of root.querySelectorAll('[title],[aria-label],[placeholder]')) {
            yield;
            considerText(el.getAttribute('title'), el, el.tagName.toLowerCase() + '[title]');
            considerText(el.getAttribute('aria-label'), el, el.tagName.toLowerCase() + '[aria-label]');
            considerText(el.getAttribute('placeholder'), el, el.tagName.toLowerCase() + '[placeholder]');
        }
    }
    // Sentence-container pass: catch sentences the game splits across inline
    // elements (company-name links etc.) — see file header. Check root itself
    // too, not just descendants, since a MutationObserver addedNodes entry is
    // often the sentence container element itself.
    if (root.nodeType === 1) {
        if (hasMixedInlineContent(root)) considerSentence(root);
        if (root.querySelectorAll) {
            const elements = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
            let el;
            while ((el = elements.nextNode())) {
                yield;
                if (hasMixedInlineContent(el)) considerSentence(el);
            }
        }
    }
}

// Keep DOM capture out of mutation microtasks. A generator retains wrapped-line
// buffering across slices; scanning a large table must not block keyboard input.
const scanRoots = new Set();
let scanJob = null, scanTimer = null;
function queueScan(root) {
    if (!root || window.__WSR_UI_SCAN__ === false) return;
    scanRoots.add(root);
    if (scanTimer === null) scanTimer = setTimeout(drainScans, 16);
}
function drainScans() {
    scanTimer = null;
    if (window.__WSR_UI_SCAN__ === false) {
        scanRoots.clear(); scanJob = null; return;
    }
    const start = performance.now();
    do {
        if (!scanJob) {
            const root = scanRoots.values().next().value;
            if (!root) break;
            scanRoots.delete(root);
            if (!root.isConnected) continue;
            scanJob = root.nodeType === 3 ? (function* () {
                considerText(root.nodeValue, root.parentElement);
            })() : scanNodeSteps(root);
        }
        if (scanJob.next().done) scanJob = null;
    } while (performance.now() - start < 4);
    if (scanJob || scanRoots.size) scanTimer = setTimeout(drainScans, 16);
}

function fullScan() {
    const root = document.body;
    if (!scanJob && !scanRoots.size) queueScan(root);
}

if (enabled) {
    const start = () => {
        fullScan();
        const observer = new MutationObserver((mutations) => {
            if (typeof window !== 'undefined' && window.__WSR_UI_SCAN__ === false) return;
            for (const m of mutations) {
                for (const n of m.addedNodes) {
                    if (n.nodeType === 1 || n.nodeType === 3) queueScan(n);
                }
                if (m.type === 'characterData' && m.target) {
                    queueScan(m.target);
                }
                if (m.type === 'attributes') queueScan(m.target);
            }
        });
        const root = document.body;
        observer.observe(root, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['title', 'aria-label', 'placeholder'] });
        // Periodic re-scan as a safety net for anything the observer missed
        // (e.g. attribute changes on nodes not covered above).
        setInterval(fullScan, 15000);
    };
    if (document.readyState === 'complete' || document.readyState === 'interactive') start();
    else document.addEventListener('DOMContentLoaded', start);

    window.addEventListener('beforeunload', flushPending);
}

if (typeof window !== 'undefined') {
    window.__WSR_UI_SCAN__ = enabled;
    window.__WSR_UI_SCAN_STATS__ = () => ({
        confirmed: confirmed.size,
        sentences: sentenceSeen.size,
        scanned: scannedTexts.size,
        newCandidates: newCandidateSeen.size,
        dictionarySize: DICT_KEYS.size,
        pendingWrite: pending.length,
        pendingWriteNew: pendingNew.length,
        csvPath: CSV_PATH,
        csvPathNew: CSV_PATH_NEW,
    });
}
