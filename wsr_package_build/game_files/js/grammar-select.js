/**
 * Target-only agreement selectors, independent of English {a|b} choices.
 * {{@ASSET.gender|f=nouvelle|m=nouveau|other=nouveau}}
 * {{@COUNT.plural|0=aucune action|one=action|other=actions}}
 * References are 1-based (@ASSET2); unnumbered references mean the first
 * capture and never consume a token. Branches cannot nest selectors/choices.
 */
const SELECTOR = /\{\{@([A-Z]+)(\d+)?\.(gender|number|agreement|plural)\|([^{}]*)\}\}/g;
const pluralRules = new Map();

export function numericValue(raw) {
    const text = String(raw).trim().replace(/,/g, '');
    return /^-?\d+(?:\.\d+)?$/.test(text) ? Number(text) : NaN;
}

export function renderGrammarSelectors(template, locale, lookup) {
    return template.replace(SELECTOR, (whole, name, index, feature, body) => {
        const options = Object.create(null);
        for (const branch of body.split('|')) {
            const equals = branch.indexOf('=');
            if (equals < 1) return whole;
            options[branch.slice(0, equals).trim()] = branch.slice(equals + 1);
        }
        if (!Object.hasOwn(options, 'other')) return whole;
        const capture = lookup(name, Number(index || 1) - 1);
        let selected;
        if (feature === 'plural' && capture) {
            const count = numericValue(capture.raw);
            if (Number.isFinite(count)) {
                if (Object.hasOwn(options, String(count))) selected = String(count);
                else {
                    if (!pluralRules.has(locale)) pluralRules.set(locale, new Intl.PluralRules(locale));
                    selected = pluralRules.get(locale).select(count);
                }
            }
        } else if (capture && capture.record) {
            selected = feature === 'agreement'
                ? `${capture.record.gender}_${capture.record.number}` : capture.record[feature];
        }
        return Object.hasOwn(options, selected) ? options[selected] : options.other;
    });
}
