/**
 * Passive template-match tester for dynamic (server-assembled) game text.
 *
 * This does NOT touch the DOM or change anything on screen — it's the
 * "does this actually work" checkpoint for template-translate.js before
 * that logic is ever wired to replace real displayed text. It watches the
 * same gameState text fields localization-capture.js already watches
 * (news headlines, advisory summaries, etc.), and for each NEW string it
 * sees, tries to match it against the templates in template-translate.js.
 * Matches (and only matches) are logged to console so you can play the
 * game normally and see, in real time, whether a given template actually
 * fires against real assembled sentences — and whether the Korean output
 * (with particle attachment) looks right.
 *
 * DevTools console (Ctrl+Shift+I):
 *   window.__WSR_TEMPLATE_MATCHES__()      // all matches seen so far
 *   window.__WSR_TEMPLATE_TEST__("text")   // manually test any string
 *   window.__WSR_TEMPLATE_UNMATCHED__()    // recent *unmatched* long lines
 *                                          // (candidates for new templates)
 */

import { matchTemplate } from './template-translate.js';

// Same field list localization-capture.js watches for dynamic text.
const TEXT_FIELDS = [
    'newsHeadlines',
    'advisorySummary',
    'financialProfile',
];

const seen = new Set();
const matches = [];
const unmatched = []; // capped ring buffer of recent non-matching long strings
const UNMATCHED_CAP = 200;
const UNMATCHED_MIN_LEN = 20; // skip short strings — too noisy, rarely template-shaped

const HAS_KOREAN = /[가-힣]/;

function scanText(text) {
    if (typeof text !== 'string') return;
    const t = text.trim();
    if (!t || seen.has(t)) return;
    if (HAS_KOREAN.test(t)) return; // already-translated Korean — skip
    seen.add(t);

    const result = matchTemplate(t);
    if (result.matched) {
        matches.push({ original: t, korean: result.korean, source: result.source });
        if (matches.length > 1000) matches.shift();
        if (window.__WSR_TEMPLATE_SCAN_LOG__ === true) console.log(`[ws-template-scan] MATCH\n  EN: ${t}\n  KO: ${result.korean}`);
    } else if (t.length >= UNMATCHED_MIN_LEN) {
        unmatched.push(t);
        if (unmatched.length > UNMATCHED_CAP) unmatched.shift();
    }
}

const pending = new Set();
let scanTimer = null;
function drainPending() {
    scanTimer = null;
    if (window.__WSR_TEMPLATE_SCAN__ === false) { pending.clear(); return; }
    const start = performance.now();
    for (const text of pending) {
        pending.delete(text);
        scanText(text);
        if (performance.now() - start >= 4) break;
    }
    if (pending.size) scanTimer = setTimeout(drainPending, 16);
}
export function scanFromGameState(state) {
    if (!state || window.__WSR_TEMPLATE_SCAN__ === false) return;
    for (const field of TEXT_FIELDS) {
        const val = state[field];
        for (const text of Array.isArray(val) ? val : [val]) {
            if (typeof text !== 'string' || HAS_KOREAN.test(text)) continue;
            const trimmed = text.trim();
            if (trimmed && !seen.has(trimmed)) pending.add(trimmed);
        }
    }
    if (pending.size && scanTimer === null) scanTimer = setTimeout(drainPending, 16);
}

if (typeof window !== 'undefined') {
    window.__WSR_TEMPLATE_MATCHES__ = () => matches.slice();
    window.__WSR_TEMPLATE_UNMATCHED__ = () => unmatched.slice();
    window.__WSR_TEMPLATE_TEST__ = (str) => matchTemplate(str);
}
