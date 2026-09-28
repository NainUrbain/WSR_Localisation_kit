// Run: node --experimental-vm-modules tests/runtime.test.cjs [runtime-js-dir]
// Game imports are stubbed; the real translation engine and language modules run.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function main() {
    const root = path.resolve(process.argv[2] || path.join(__dirname, '../game_files/js'));
    const context = vm.createContext({ console, localeCode: 'fr-FR' });
    const cache = new Map();
    function get(file) {
        if (cache.has(file)) return cache.get(file);
        const source = file.endsWith('localeManager.js')
            ? 'export default {getCurrentLocale:()=>globalThis.localeCode};'
            : fs.readFileSync(file, 'utf8');
        const module = new vm.SourceTextModule(source, { context, identifier: file });
        cache.set(file, module);
        return module;
    }
    const module = get(path.join(root, 'template-translate.js'));
    await module.link((specifier, parent) => get(path.resolve(path.dirname(parent.identifier), specifier)));
    await module.evaluate();
    const engine = module.namespace;
    const registry = get(path.join(root, 'locale-registry.js')).namespace;
    let assertions = 0;
    function check(locale, source, target, actual, expected, extra = {}) {
        if (!registry.LANGUAGE_RULES[locale]) return; // A player stage contains one locale.
        context.localeCode = locale;
        engine.setRuntimeLocaleTemplates(locale, { templates: [{ key: 'test', source, target }], ...extra });
        const result = engine.matchTemplate(actual);
        assert.equal(result.matched, true, actual);
        assert.equal(result.korean, expected, actual);
        assertions++;
    }
    const entities = { ASSET: {
        BANK: { target: 'banque', gender: 'f', number: 'sg', forms: { PL: 'banques', GENITIVE: 'de banque' } },
        MILL: { target: 'moulin', gender: 'm', number: 'sg' },
        BANKS: { target: 'banques', gender: 'f', number: 'pl' },
        FACTORY: { target: 'usine', gender: 'f', number: 'sg' },
    } };
    const adj = '{{@ASSET.agreement|f_sg=nouvelle|m_sg=nouveau|f_pl=nouvelles|m_pl=nouveaux|other=moderne}}';
    for (const [word, expected] of [['bank', 'la banque est nouvelle.'], ['mill', 'le moulin est nouveau.'], ['factory', 'l’usine est nouvelle.']]) {
        check('fr-FR', 'The @ASSET is new.', `@ASSET:DEF est ${adj}.`, `The ${word} is new.`, expected, { entities });
    }
    check('fr-FR', 'The @ASSET are new.', `@ASSET:DEF sont ${adj}.`, 'The banks are new.', 'les banques sont nouvelles.', { entities });
    check('fr-FR', 'The @ASSET is new.', `@ASSET:DEF est ${adj}.`, 'The shop is new.', 'shop est moderne.', { entities });
    check('fr-FR', 'Buy @ASSET.', '@ASSET:FORM_PL:DEF', 'Buy bank.', 'les banques', { entities });
    check('fr-FR', 'Buy @ASSET.', '@ASSET:FORM_GENITIVE', 'Buy bank.', 'de banque', { entities });
    check('fr-FR', 'Buy @ASSET.', '@ASSET:A', 'Buy factory.', 'à l’usine', { entities });
    const plural = '@COUNT {{@COUNT.plural|0=aucune action|one=action|other=actions}}';
    for (const [n, expected] of [[0, '0 aucune action'], [1, '1 action'], [2, '2 actions'], [1000, '1,000 actions']]) {
        check('fr-FR', 'Buy @COUNT shares.', plural, `Buy ${n} shares.`, expected);
    }
    check('fr-FR', 'The @ASSET {rises|falls}.', `@ASSET:DEF {[1]monte|baisse} {{@ASSET.gender|f=seule|other=seul}}.`,
        'The bank falls.', 'la banque baisse seule.', { entities });
    check('fr-FR', 'Swap @ASSET for @ASSET.', '@ASSET2:DEF / @ASSET1:DEF {{@ASSET2.gender|m=masculin|other=autre}}',
        'Swap bank for mill.', 'le moulin / la banque masculin', { entities });
    check('fr-FR', 'Month: @MONTH.', 'Mois : @MONTH.', 'Month: December.', 'Mois : décembre.');
    check('fr-FR', 'Sell @CORP {now|later}.', 'Vente de @CORP {[1]\'\'|plus tard}.', 'Sell AMP now.', 'Vente d’AMP.');
    check('ja-JP', 'Month: @MONTH.', '@MONTH月', 'Month: December.', '12月');
    check('pt-BR', 'Month: @MONTH.', '@MONTH', 'Month: December.', 'dezembro-BR');
    check('pt-PT', 'Month: @MONTH.', '@MONTH', 'Month: December.', 'dezembro-PT');
    check('ko-KR', 'Month: @MONTH.', '@MONTH월', 'Month: December.', '12월');
    check('ko-KR', '@CORP sells @AMOUNT.', '@CORP은/는 @AMOUNT을/를 매각합니다.', 'ACME sells 20.', 'ACME는 $ 20을 매각합니다.');
    check('ko-KR', '@CORP buys @CORP.', '@CORP2 / @CORP1', 'ACME buys IBM.', 'IBM / ACME');
    check('ja-JP', '@CORP buys @CORP.', '@CORP1は@CORP2を買収。', 'ACME buys IBM.', 'ACMEはIBMを買収。');
    const selectors = get(path.join(root, 'grammar-select.js')).namespace;
    for (const [n, expected] of [[1, 'one'], [2, 'few'], [5, 'many'], [21, 'one']]) {
        assert.equal(selectors.renderGrammarSelectors('{{@COUNT.plural|one=one|few=few|many=many|other=other}}', 'ru-RU', () => ({ raw: n })), expected);
        assertions++;
    }
    for (const [n, expected] of [[0, 'zero'], [1, 'one'], [2, 'two'], [3, 'few'], [11, 'many']]) {
        assert.equal(selectors.renderGrammarSelectors('{{@COUNT.plural|zero=zero|one=one|two=two|few=few|many=many|other=other}}', 'ar', () => ({ raw: n })), expected);
        assertions++;
    }
    assert.equal(registry.localeDataFile('unknown-XX', 'templates.json'), null);
    console.log(`PASS: ${assertions} runtime examples (${root})`);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
