/**
 * French article/contraction utility — the fr-FR counterpart of attachJosa.js.
 *
 * French target templates may put a modifier on an entity token to request
 * an article or a contraction chosen from that entity's metadata
 * (locales/fr-FR/vars/VAR_*.csv columns gender, number, elision):
 *
 *   @IND:DEF -> le / la / l’ / les
 *   @IND:DE  -> du / de la / de l’ / des
 *   @IND:A   -> au / à la / à l’ / aux
 *
 * Missing metadata falls back to the bare "de"/"à" form (or no article for
 * DEF) so a half-filled row never renders a wrong gender.
 */

export const FRENCH_MODIFIERS = new Set(['DEF', 'DE', 'A']);

/**
 * @param {string} value - the rendered French entity name
 * @param {string} [mode] - 'yes' | 'no' | 'auto' (fr-elision column)
 * @returns {boolean} whether le/la/de elide before this word
 */
export function frenchElides(value, mode) {
    if (mode === 'yes') return true;
    if (mode === 'no') return false;
    return /^[aeiouyàâäæéèêëîïôöœùûüÿh]/i.test(String(value).trim());
}

/**
 * @param {string} value - the rendered French entity name
 * @param {{gender?: string, number?: string, elision?: string} | null} record
 * @param {string} [modifier] - one of FRENCH_MODIFIERS; anything else returns value
 * @returns {string} value with the requested article/contraction prefixed
 */
export function attachFrenchArticle(value, record, modifier) {
    if (!modifier) return value;
    const gender = record && record.gender;
    const number = record && record.number;
    const elides = number !== 'pl' && frenchElides(value, record && record.elision);
    if (modifier === 'DE') {
        if (number === 'pl') return `des ${value}`;
        if (elides) return `de l’${value}`;
        if (gender === 'm') return `du ${value}`;
        if (gender === 'f') return `de la ${value}`;
        return `de ${value}`;
    }
    if (modifier === 'A') {
        if (number === 'pl') return `aux ${value}`;
        if (elides) return `à l’${value}`;
        if (gender === 'm') return `au ${value}`;
        if (gender === 'f') return `à la ${value}`;
        return `à ${value}`;
    }
    if (modifier === 'DEF') {
        if (number === 'pl') return `les ${value}`;
        if (elides) return `l’${value}`;
        if (gender === 'm') return `le ${value}`;
        if (gender === 'f') return `la ${value}`;
    }
    return value;
}

/* --------------------------- self-test --------------------------- */
// Uncomment to sanity-check in a Node REPL:
// console.log(attachFrenchArticle('banque', { gender: 'f', number: 'sg' }, 'DE'));   // de la banque
// console.log(attachFrenchArticle('acier', { gender: 'm', number: 'sg' }, 'A'));     // à l’acier
// console.log(attachFrenchArticle('Pays-Bas', { gender: 'm', number: 'pl' }, 'A'));  // aux Pays-Bas
// console.log(attachFrenchArticle('Japon', { gender: 'm', number: 'sg' }, 'DEF'));   // le Japon
