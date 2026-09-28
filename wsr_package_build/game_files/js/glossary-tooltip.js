
import localeManager from './locale/localeManager.js';
import { localeDataFile } from './locale-registry.js';

const _require = (typeof require !== 'undefined') ? require : null;
const fs = _require ? _require('fs') : null;
const path = _require ? _require('path') : null;

// Per-locale files: locale/<prefix>-glossary.json and <prefix>-header-glossary.json.
const localeFile = (suffix) => localeDataFile(localeManager.getCurrentLocale(), suffix);
let glossaryCache = null;
let headerGlossaryCache = null;
let glossaryLocale = null;
const warnedMissing = new Set();

// Mirrors dom-translate-hook.js's readJsonNear() — __dirname isn't
// reliably this file's own folder depending on how the renderer bundles/
// serves JS, so every plausible location is tried.
function readJsonNear(fileName) {
    if (!fs || !path || !fileName) return {};
    const candidates = [
        path.join(__dirname, 'locale', fileName),
        path.join(__dirname, 'js', 'locale', fileName),
        path.join(__dirname, '..', 'locale', fileName),
        path.join(__dirname, '..', 'js', 'locale', fileName),
    ];
    for (const filePath of candidates) {
        try {
            if (!fs.existsSync(filePath)) continue;
            const raw = fs.readFileSync(filePath, 'utf8');
            console.log(`[glossary-tooltip] loaded ${fileName} from ${filePath}`);
            return JSON.parse(raw);
        } catch (e) {
            // try next candidate
        }
    }
    console.error(`[glossary-tooltip] failed to load ${fileName} — tried:`, candidates);
    return {};
}

function glossary() {
    const locale = localeManager.getCurrentLocale();
    if (locale !== glossaryLocale) {
        glossaryLocale = locale;
        glossaryCache = null;
        headerGlossaryCache = null;
    }
    if (!glossaryCache) glossaryCache = readJsonNear(localeFile('glossary.json'));
    if (!headerGlossaryCache) headerGlossaryCache = readJsonNear(localeFile('header-glossary.json'));
    // Merged view, rebuilt lazily whenever either cache was just (re)loaded --
    // header entries first so a same-named financial term (unlikely, but not
    // impossible) always wins, matching pre-split behavior where header rows
    // were appended into the same ko-glossary.json dict.
    return Object.assign({}, headerGlossaryCache, glossaryCache);
}

const HAS_HIGHLIGHT_API =
    typeof window !== 'undefined' &&
    typeof window.Highlight === 'function' &&
    typeof CSS !== 'undefined' &&
    !!CSS.highlights &&
    typeof document !== 'undefined' &&
    typeof document.caretRangeFromPoint === 'function';

// node -> [{ range, term, def }]  (Map, not WeakMap — must be iterable for
// the periodic "drop disconnected nodes" sweep; see file header, "MEMORY").
const nodeRanges = new Map();
let termHighlight = null;
let missingHighlight = null;

let initialized = false;
let tipEl = null;

function ensureInit() {
    if (initialized || typeof document === 'undefined') return;
    initialized = true;

    const style = document.createElement('style');
    style.textContent = `
        ::highlight(wsr-glossary) {
            text-decoration: underline;
            text-decoration-style: dotted;
            text-decoration-color: #7a7fd6;
        }
        ::highlight(wsr-glossary-missing) {
            text-decoration: underline;
            text-decoration-style: dotted;
            text-decoration-color: #d67a7a;
        }
        .wsr-glossary-term {
            text-decoration: underline dotted #7a7fd6 1.5px;
            text-underline-offset: 2px;
            cursor: help;
        }
        .wsr-glossary-term.wsr-glossary-missing {
            text-decoration-color: #d67a7a;
        }
        .wsr-glossary-tooltip {
            position: fixed;
            z-index: 999999;
            max-width: 300px;
            padding: 8px 12px;
            background: #2a2c3d;
            color: #f4f4f8;
            font-size: 12.5px;
            line-height: 1.5;
            border-radius: 6px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
            pointer-events: none;
            border: 1px solid #444862;
        }
    `;
    document.head.appendChild(style);

    tipEl = document.createElement('div');
    tipEl.className = 'wsr-glossary-tooltip';
    tipEl.style.display = 'none';
    document.body.appendChild(tipEl);

    function showAt(x, y, def) {
        tipEl.textContent = def;
        tipEl.style.display = 'block';
        const tr = tipEl.getBoundingClientRect();
        let top = y - tr.height - 16;
        if (top < 0) top = y + 16;
        let left = x - tr.width / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - tr.width - 8));
        tipEl.style.top = top + 'px';
        tipEl.style.left = left + 'px';
    }
    function hide() {
        tipEl.style.display = 'none';
        if (document.body.style.cursor === 'help') document.body.style.cursor = '';
    }

    if (HAS_HIGHLIGHT_API) {
        termHighlight = new window.Highlight();
        missingHighlight = new window.Highlight();
        CSS.highlights.set('wsr-glossary', termHighlight);
        CSS.highlights.set('wsr-glossary-missing', missingHighlight);

        let lastHit = null;
        let hoverFrame = 0;
        let hoverX = 0;
        let hoverY = 0;
        document.addEventListener('mousemove', (e) => {
            hoverX = e.clientX;
            hoverY = e.clientY;
            if (hoverFrame) return;
            hoverFrame = requestAnimationFrame(() => {
                hoverFrame = 0;
                if (!nodeRanges.size) return;
                const range = document.caretRangeFromPoint(hoverX, hoverY);
                const node = range && range.startContainer;
                const entries = node && node.nodeType === 3 ? nodeRanges.get(node) : null;
                const offset = range ? range.startOffset : -1;
                const hit = entries ? entries.find((r) => offset >= r.start && offset <= r.end) : null;
                if (hit) {
                    if (hit !== lastHit) {
                        lastHit = hit;
                        document.body.style.cursor = 'help';
                    }
                    showAt(hoverX, hoverY, hit.def);
                } else if (lastHit) {
                    lastHit = null;
                    hide();
                }
            });
        }, { passive: true });

        // See file header, "MEMORY" — bounds how long a disconnected
        // node's Range can keep it (and the highlight entry) alive.
        setInterval(() => {
            for (const [node, entries] of nodeRanges) {
                if (node.isConnected) continue;
                for (const { range, term, def } of entries) {
                    (def ? termHighlight : missingHighlight).delete(range);
                }
                nodeRanges.delete(node);
            }
        }, 5000);
    } else {
        // Fallback: whole-parent-element marking (see file header).
        document.addEventListener('mouseenter', (e) => {
            const el = e.target;
            if (el.classList && el.classList.contains('wsr-glossary-term')) {
                const def = el.getAttribute('data-wsr-glossary-def');
                if (def) showAt(e.clientX, e.clientY, def);
            }
        }, true);
        document.addEventListener('mouseleave', (e) => {
            const el = e.target;
            if (el.classList && el.classList.contains('wsr-glossary-term')) hide();
        }, true);
    }
}

const TAG_PATTERN = /\[([^\[\]]*)\(!([\s\S]*?)\)\]|\[!([^\]]+)\]/g;

/**
 * If `text` (the RAW value about to be written to `node`) contains one or
 * more [!단어] tags: writes the tag-stripped plain text to `node.nodeValue`
 * (same safe, Preact-invisible mutation every other pass in
 * dom-translate-hook.js already relies on), then marks each tagged word's
 * exact character span via the CSS Custom Highlight API (or, if
 * unavailable, the whole parent element) so it can be hovered for a
 * tooltip — see file header for why neither approach ever adds/removes/
 * replaces a DOM node. Returns true if at least one tag was found (caller
 * should treat the node as fully handled), false (no-op) otherwise.
 */
export function applyGlossaryTags(node, text) {
    if (!text || (text.indexOf('[!') === -1 && text.indexOf('(!') === -1)) return false;
    if (!node || node.nodeType !== 3) return false;

    ensureInit();
    const dict = glossary();

    // Build the tag-stripped plain string while recording each term's
    // [start, end) offset IN THAT OUTPUT STRING (not the input — the
    // bracket/exclaim markers before it shift everything).
    let plain = '';
    let cursor = 0;
    const found = [];
    TAG_PATTERN.lastIndex = 0;
    let m;
    while ((m = TAG_PATTERN.exec(text)) !== null) {
        plain += text.slice(cursor, m.index);
        const start = plain.length;
        // m[1]/m[2] set for [표시(!key)]; m[3] set for legacy [!단어]
        // (display text and lookup key are the same in the legacy case).
        const display = m[1] !== undefined ? m[1] : m[3];
        const key = m[2] !== undefined ? m[2] : m[3];
        plain += display;
        found.push({ start, end: plain.length, term: key });
        cursor = m.index + m[0].length;
    }
    if (found.length === 0) return false;
    plain += text.slice(cursor);

    // Safe: mutates the SAME Text node's content in place, exactly like
    // every other translated-text write in dom-translate-hook.js.
    node.nodeValue = plain;

    for (const { term } of found) {
        if (!dict[term] && !warnedMissing.has(term)) {
            warnedMissing.add(term);
            console.warn(`[glossary-tooltip] missing definition for "${term}" (${localeFile('glossary.json')})`);
        }
    }

    if (HAS_HIGHLIGHT_API) {
        // Re-processing the same node (e.g. re-entrant safety net) — drop
        // whatever ranges it had before so they don't accumulate.
        const prev = nodeRanges.get(node);
        if (prev) {
            for (const { range, def } of prev) (def ? termHighlight : missingHighlight).delete(range);
        }
        const entries = [];
        for (const { start, end, term } of found) {
            const def = dict[term] || `⚠ No definition for "${term}" in ${localeFile('glossary.json')}`;
            const range = new Range();
            try {
                range.setStart(node, start);
                range.setEnd(node, end);
            } catch (e) {
                continue; // offsets somehow out of bounds — skip this one term, not the whole node
            }
            (dict[term] ? termHighlight : missingHighlight).add(range);
            entries.push({ range, term, def, start, end });
        }
        nodeRanges.set(node, entries);
    } else {
        // Fallback: mark the nearest EXISTING element (additive only —
        // never touches DOM structure). Imprecise if this node mixes
        // multiple different tagged terms (last one wins) — see file
        // header, acceptable degradation on very old Chromium only.
        const el = node.parentElement;
        if (el) {
            const last = found[found.length - 1];
            const def = dict[last.term];
            el.classList.add('wsr-glossary-term');
            el.classList.toggle('wsr-glossary-missing', !def);
            el.setAttribute('data-wsr-glossary-def', def || `⚠ No definition for "${last.term}" in ${localeFile('glossary.json')}`);
        }
    }
    return true;
}

// Same "reload from disk without restarting" convenience as
// dom-translate-hook.js's __WSR_DOM_TRANSLATE_RELOAD__.
if (typeof window !== 'undefined') {
    window.__WSR_GLOSSARY_RELOAD__ = () => {
        glossaryCache = null;
        headerGlossaryCache = null;
        return Object.keys(glossary()).length;
    };
}
