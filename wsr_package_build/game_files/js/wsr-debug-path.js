const _require = (typeof require !== 'undefined') ? require : null;
const fs = _require ? _require('fs') : null;
const path = _require ? _require('path') : null;

// Written by install_patch.py for developer installs only; it points at
// wsr_package_build/debug_output. Without it, debug dumps are disabled.
const CONFIG_NAME = 'wsr-kr-debug-config.json';

// Same __dirname-candidates trick as dom-translate-hook.js's readJsonNear()
// (__dirname doesn't reliably point at js/ in this app's bundling setup).
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
            if (cfg && typeof cfg.debugDir === 'string' && cfg.debugDir) return cfg.debugDir;
        } catch (e) {
            // try next candidate
        }
    }
    return null;
}

let cachedDir; // undefined = not looked up yet, null = no config found

/** @returns {string|null} absolute path for a debug dump file, or null when disabled */
export function resolveDebugPath(fileName) {
    if (!path) return null;
    if (cachedDir === undefined) cachedDir = readConfiguredDir();
    return cachedDir ? path.join(cachedDir, fileName) : null;
}
