
const _require = (typeof require !== 'undefined') ? require : null;
const fs = _require ? _require('fs') : null;
const path = _require ? _require('path') : null;
const os = _require ? _require('os') : null;

const CONFIG_NAME = 'wsr-kr-capture-config.json';

// Same __dirname-candidates trick as dom-translate-hook.js's readJsonNear()
// (see the comment there: __dirname doesn't reliably point at js/ in this
// app's bundling setup, so try every plausible location).
function readConfiguredDir() {
    if (!fs || !path || typeof __dirname === 'undefined') return null;
    const candidates = [
        path.join(__dirname, 'locale', CONFIG_NAME),
        path.join(__dirname, 'js', 'locale', CONFIG_NAME),
        path.join(__dirname, '..', 'locale', CONFIG_NAME),
        path.join(__dirname, '..', 'js', 'locale', CONFIG_NAME),
    ];
    for (const p of candidates) {
        try {
            if (!fs.existsSync(p)) continue;
            const cfg = JSON.parse(fs.readFileSync(p, 'utf8'));
            if (cfg && typeof cfg.captureDir === 'string' && cfg.captureDir) {
                console.log(`[wsr-capture-path] captureDir from config: ${cfg.captureDir}`);
                return cfg.captureDir;
            }
        } catch (e) {
            // try next candidate
        }
    }
    return null;
}

let cachedDir; // undefined = not looked up yet, null = no config found

export function resolveCapturePath(envValue, fileName) {
    if (envValue) return envValue;
    if (!path) return null;
    if (cachedDir === undefined) cachedDir = readConfiguredDir();
    if (cachedDir) return path.join(cachedDir, fileName);
    const fallback = os ? path.join(os.homedir(), 'AppData', 'Local', 'WSR_KR_capture', fileName) : null;
    return fallback;
}
