/**
 * Korean josa (조사) attachment utility.
 *
 * Given a word ending in Korean text (or a number/Latin fallback) and a
 * particle pair, returns the word with the grammatically correct particle
 * attached — decided by whether the last syllable has a batchim (받침),
 * not by a fixed suffix. Because it runs on the substituted value at
 * runtime, it works for any word, including company names.
 *
 * Hangul syllable math: for a precomposed syllable in the range
 * U+AC00–U+D7A3, index = code - 0xAC00. index % 28 == 0 means no final
 * consonant (받침 없음) -> vowel-ending particle. Anything else -> a
 * consonant-ending particle, except the (으)로 pair, which additionally
 * treats a final ㄹ (jong index 8) as if there were no batchim.
 */

const HANGUL_BASE = 0xAC00;
const HANGUL_LAST = 0xD7A3;
const JONG_COUNT = 28;

// jong index 0 = no batchim, 8 = ㄹ
function hasBatchim(codePoint) {
    if (codePoint < HANGUL_BASE || codePoint > HANGUL_LAST) return null; // not a precomposed syllable
    const jong = (codePoint - HANGUL_BASE) % JONG_COUNT;
    return jong !== 0;
}

function jongIndex(codePoint) {
    if (codePoint < HANGUL_BASE || codePoint > HANGUL_LAST) return null;
    return (codePoint - HANGUL_BASE) % JONG_COUNT;
}

// Rough fallback for words that don't end in a precomposed Hangul syllable
// (Latin company names not yet transliterated, raw numbers, etc). Numbers
// are mapped by their spoken Korean final sound for the last digit.
//
// Sino-Korean digit pronunciation batchim table (last spoken syllable):
// 0 영(ㅇ, treat as batchim-present for topic/subject particles per convention)
// 1 일(ㄹ) batchim=true   2 이 batchim=false      3 삼(ㅁ) batchim=true
// 4 사 batchim=false      5 오 batchim=false      6 육(ㄱ) batchim=true
// 7 칠(ㄹ) batchim=true   8 팔(ㄹ) batchim=true   9 구 batchim=false
const DIGIT_BATCHIM_FIXED = {
    '0': true, '1': true, '2': false, '3': true, '4': false,
    '5': false, '6': true, '7': true, '8': true, '9': false,
};

function guessBatchimForNonHangul(word) {
    const last = word.trim().slice(-1);
    if (/[0-9]/.test(last)) return DIGIT_BATCHIM_FIXED[last];
    return false;
}

/**
 * @param {string} word - the word/phrase the particle attaches to
 * @param {[string, string]} pair - [withBatchim, withoutBatchim], e.g. ["은","는"]
 * @param {object} [opts]
 * @param {boolean} [opts.assumeBatchim] - override for non-Hangul endings
 * @returns {string} particle only (not concatenated) - caller does `word + particle`
 */
export function pickJosa(word, pair, opts = {}) {
    if (!word) return pair[1];
    const cp = word.codePointAt(word.length - 1);
    const batchim = hasBatchim(cp);
    if (batchim === null) {
        const fallback = opts.assumeBatchim !== undefined ? opts.assumeBatchim : guessBatchimForNonHangul(word);
        return fallback ? pair[0] : pair[1];
    }
    return batchim ? pair[0] : pair[1];
}

/** Convenience: returns word + correct particle already attached. */
export function attachJosa(word, pair, opts = {}) {
    return word + pickJosa(word, pair, opts);
}

// Common particle pairs, [withBatchim, withoutBatchim]
export const JOSA = {
    TOPIC: ['은', '는'],       // 은/는
    SUBJECT: ['이', '가'],     // 이/가
    OBJECT: ['을', '를'],      // 을/를
    AND: ['과', '와'],         // 과/와
    ALSO_EVEN: ['이나', '나'], // 이나/나 (approx "or/even")
};

/**
 * (으)로 is a special case: treated as "no batchim" whenever the final
 * consonant is either absent OR is ㄹ (jong index 8) — e.g. "서울로" not
 * "서울으로". Use this instead of pickJosa/JOSA for -(으)로.
 */
export function attachRo(word) {
    if (!word) return word + '로';
    const cp = word.codePointAt(word.length - 1);
    const jong = jongIndex(cp);
    if (jong === null) {
        return word + (guessBatchimForNonHangul(word) ? '으로' : '로');
    }
    return (jong === 0 || jong === 8) ? word + '로' : word + '으로';
}

/* --------------------------- self-test --------------------------- */
// Uncomment to sanity-check in a Node REPL:
// console.log(attachJosa('프랑스', JOSA.TOPIC));   // 프랑스는
// console.log(attachJosa('한국', JOSA.TOPIC));      // 한국은
// console.log(attachJosa('은행', JOSA.SUBJECT));    // 은행이
// console.log(attachJosa('반도체', JOSA.OBJECT));   // 반도체를
// console.log(attachRo('서울'));                    // 서울로
// console.log(attachRo('한국'));                    // 한국으로
