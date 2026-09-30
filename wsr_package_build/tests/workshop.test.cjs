// node --experimental-vm-modules tests/workshop.test.cjs <release> <game-resources/app>
// Runs the installed game's actual overlay loader/protocol on disposable data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { pathToFileURL } = require('node:url');

async function main() {
    const release = path.resolve(process.argv[2]);
    const app = path.resolve(process.argv[3]);
    const content = path.join(release, 'content');
    const report = JSON.parse(fs.readFileSync(path.join(release, 'build-report.json')));
    for (const [rel, hash] of Object.entries(report.content_sha256)) {
        assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(content, rel))).digest('hex'), hash, rel);
    }
    assert.ok(fs.existsSync(path.join(content, 'js/app.js')));
    assert.ok(!fs.existsSync(path.join(content, 'game_files')));
    // Link the entire game module graph against the overlay. No game executes.
    const linkContext = vm.createContext({});
    const linkCache = new Map();
    function gameModule(rel) {
        if (linkCache.has(rel)) return linkCache.get(rel);
        const overlay = path.join(content, rel);
        const file = fs.existsSync(overlay) ? overlay : path.join(app, rel);
        const mod = new vm.SourceTextModule(fs.readFileSync(file, 'utf8'), {context: linkContext, identifier: rel});
        linkCache.set(rel, mod);
        return mod;
    }
    await gameModule('js/app.js').link((spec, parent) => {
        assert.ok(spec.startsWith('.'), `Unexpected external module: ${spec}`);
        return gameModule(path.posix.normalize(path.posix.join(path.posix.dirname(parent.identifier), spec)));
    });

    // Evaluate real locale manager + translation engines without Node require,
    // __dirname, disk JSON, or Electron. Only the game's REST client is stubbed.
    const context = vm.createContext({console, location: {search: '?locale=ko-KR'}, URLSearchParams});
    const cache = new Map();
    function runtime(rel) {
        if (cache.has(rel)) return cache.get(rel);
        let source = rel === 'js/api.js' ? 'export const setLocale = async () => {};' :
            fs.readFileSync(fs.existsSync(path.join(content, rel)) ? path.join(content, rel) : path.join(app, rel), 'utf8');
        if (rel === 'js/dom-translate-hook.js') source += '\nexport {loadLocaleData, loadHeaderTerms, loadHeaderLines, processTextNode};';
        if (rel === 'js/glossary-tooltip.js') source += '\nexport {glossary};';
        const mod = new vm.SourceTextModule(source, {context, identifier: rel});
        cache.set(rel, mod);
        return mod;
    }
    const dom = runtime('js/dom-translate-hook.js');
    await dom.link((spec, parent) => runtime(path.posix.normalize(path.posix.join(path.posix.dirname(parent.identifier), spec))));
    await dom.evaluate();
    const locale = cache.get('js/locale/localeManager.js').namespace.default;
    assert.equal(locale.getCurrentLocale(), 'ko-KR');
    assert.ok(locale.getLanguageOptions()['ko-KR']);
    const hook = dom.namespace.loadLocaleData('ko-KR');
    assert.ok(Object.keys(hook.exact).length > 2000);
    const source = Object.keys(hook.exact).find(s => s === 'New Game') ||
        Object.keys(hook.exact).find(s => /^[A-Z][a-z]+ [A-Z][a-z]+$/.test(s));
    const node = {nodeType: 3, nodeValue: source, parentElement: null};
    dom.namespace.processTextNode(node);
    assert.equal(node.nodeValue, hook.exact[source]);
    assert.ok(dom.namespace.loadHeaderTerms().length > 0);
    assert.ok(Object.keys(dom.namespace.loadHeaderLines()).length > 0);
    assert.ok(Object.keys(cache.get('js/glossary-tooltip.js').namespace.glossary()).length > 0);
    const engine = cache.get('js/template-translate.js').namespace;
    assert.equal(engine.activateLocale('ko-KR'), true);
    assert.ok(engine.TEMPLATES.length > 2000);
    const sample = engine.TEMPLATES.find(t => !/[@{}]/.test(t.source) && t.source.length > 15);
    assert.ok(sample, 'Need a real compiled template example');
    assert.equal(engine.matchTemplate(sample.source).matched, true);
    locale.syncFromGameState('en-US');
    assert.equal(dom.namespace.loadLocaleData('en-US'), null);
    const english = {nodeType: 3, nodeValue: source, parentElement: null};
    dom.namespace.processTextNode(english);
    assert.equal(english.nodeValue, source);

    const scratch = fs.mkdtempSync(path.join(path.dirname(release), '.workshop-test-'));
    assert.equal(path.dirname(scratch), path.dirname(release));
    try {
        let items = [{id: '123456', installed: true, folder: content}];
        const loaderModule = {exports: {}};
        vm.runInNewContext(fs.readFileSync(path.join(app, 'workshopLoader.js'), 'utf8'), {
            require, module: loaderModule, console, AbortController, setTimeout, clearTimeout,
            fetch: async () => ({ok: true, status: 200, json: async () => ({items})}),
        });
        const loader = loaderModule.exports;
        const result = await loader.applyWorkshopOverlay({restBase: 'http://test.invalid', userDataDir: scratch});
        assert.equal(result.ok, true);
        assert.equal(result.modsLoaded, 1);
        let handler;
        const protocolModule = {exports: {}};
        vm.runInNewContext(fs.readFileSync(path.join(app, 'workshopProtocol.js'), 'utf8'), {
            require: name => name === 'electron' ? {protocol: {
                isProtocolIntercepted: () => false,
                interceptFileProtocol: (_, fn) => { handler = fn; return true; },
            }} : name === './workshopLoader' ? loader : require(name),
            module: protocolModule, console, process: {env: {}},
        });
        assert.equal(protocolModule.exports.registerWorkshopProtocol({appRoot: app, userDataDir: scratch}), true);
        function resolve(rel) {
            let served;
            handler({url: pathToFileURL(path.join(app, rel)).href}, result => { served = result.path; });
            return served;
        }
        for (const rel of Object.keys(report.content_sha256)) {
            assert.equal(resolve(rel), path.join(scratch, 'workshop/overlay', rel));
        }
        assert.equal(resolve('js/locale/translator.js'), path.join(app, 'js/locale/translator.js'));
        items = [];
        assert.equal((await loader.applyWorkshopOverlay({restBase: 'http://test.invalid', userDataDir: scratch})).modsLoaded, 0);
        assert.equal(resolve('js/app.js'), path.join(app, 'js/app.js'));
    } finally {
        // Only the verified disposable directory under the release parent.
        fs.rmSync(scratch, {recursive: true, force: true});
    }
    console.log(`PASS: ${linkCache.size} game modules linked; Korean UI/templates/tooltips without fs; actual Workshop loader/protocol and unsubscribe verified`);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
