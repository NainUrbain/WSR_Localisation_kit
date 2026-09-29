/**
 * French (fr-FR) language rules — see lang-base.js for the interface.
 *
 * Articles and contractions come from token modifiers (`@IND:DEF`,
 * `@IND:DE`, `@IND:A`) resolved with the entity's gender / number /
 * elision metadata (locales/fr-FR/vars/*.csv) by frenchArticles.js.
 */
import { attachFrenchArticle, FRENCH_MODIFIERS } from './frenchArticles.js';
import { BASE_RULES, MONTH_NAMES, parseDateToken, parseBareDate, parseMonthDay } from './lang-base.js';

const MOIS = [
    'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
];
const dayFr = (day) => (Number(day) === 1 ? '1er' : String(Number(day)));

export const FR_RULES = {
    ...BASE_RULES,
    month: (raw) => MOIS[MONTH_NAMES.indexOf(raw.trim().toLowerCase())] || raw,
    attach(value, { modifier, record }) {
        return modifier && FRENCH_MODIFIERS.has(modifier)
            ? attachFrenchArticle(value, record, modifier)
            : value;
    },
    dateToken(raw) {
        const d = parseDateToken(raw);
        return d ? `${dayFr(d.day)} ${MOIS[d.month - 1]} ${d.year}` : raw;
    },
    formatDate(raw) {
        const d = parseBareDate(raw);
        return d ? `${dayFr(d.day)} ${MOIS[d.month - 1]} ${d.year}${d.suffix}` : raw;
    },
    monthDay(raw) {
        const d = parseMonthDay(raw);
        return d ? `${dayFr(d.day)} ${MOIS[d.month - 1]}` : raw;
    },
    // "de" elides before a vowel-initial name or ticker (d’AMP, d’IGCM), and an
    // empty optional choice must not leave a space before "." or ",".
    finish: (text) => text
        .replace(/\bde ([AEIOUYÀÂÉÈÊÎÔÛ])/g, 'd’$1')
        .replace(/ +([.,])(?=\s|$)/g, '$1'),
    possessive: (owner, label, body) => `${label.replace(/\s*:\s*$/, '')} (${owner}) : ${body}`,
    nativeScript: /[àâçéèêëîïôûùüÿœæ]/i,
    entityAliases: [
        [/\bThe company\b/g, 'La société'],
        [/\bthe company\b/g, 'la société'],
    ],
    memoPreamble: (company) => `NOTE INTERNE À L’ACTIONNAIRE DE CONTRÔLE DE : ${company}\n`,
};
