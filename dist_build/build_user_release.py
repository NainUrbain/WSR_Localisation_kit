"""Stage the player release for one locale: stripped runtime + that locale's data.

    python build_user_release.py --source <wsr_package_build> [--locale ko-KR] [--output DIR]

The locale's runtime data is regenerated from its CSV files (runtime_data.py)
straight into the staging folder, so the release never depends on whether
the developer build was run first.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser()
parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1] / "wsr_package_build"))
parser.add_argument("--output", default=str(Path(__file__).parent / "user_release"))
parser.add_argument("--locale", default="ko-KR")
args = parser.parse_args()
B = Path(args.source).resolve()
S = Path(args.output).resolve()
sys.path.insert(0, str(B / "pipeline_tools"))
import runtime_data  # noqa: E402
import locale_framework  # noqa: E402
from translation_csvs import audit_files  # noqa: E402

prefix = runtime_data.profile_for(args.locale)["data_prefix"]
if not audit_files() or not locale_framework.audit(args.locale):
    raise SystemExit("release stopped because locale validation failed")
if S == B or B.is_relative_to(S) or S.is_relative_to(B / "game_files"):
    raise SystemExit("output must not overlap source runtime files")
S.mkdir(parents=True, exist_ok=True)
if (S / "game_files").exists():
    shutil.rmtree(S / "game_files")
code = ["dom-translate-hook.js", "glossary-tooltip.js", "template-translate.js", "template-apply.js",
        "lang-base.js", "grammar-select.js"]
for f in code:
    dst = S / "game_files/js" / f
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(B / "game_files/js" / f, dst)

# Fresh locale data from the authoritative CSVs, written into the stage.
runtime_data.LOCALE_JS_DIR = str(S / "game_files/js/locale")
(S / "game_files/js/locale").mkdir(parents=True, exist_ok=True)
written = runtime_data.write_locale_runtime(args.locale) + [runtime_data.write_locale_list([args.locale])]
data_files = ["locale/" + Path(p).name for p in written]
runtime_data.write_registry(S / "game_files/js", [args.locale])
files = code + ["locale-registry.js"] + data_files


def read(f):
    return (S / "game_files/js" / f).read_text(encoding="utf-8").replace("\r\n", "\n")


def write(f, t):
    (S / "game_files/js" / f).write_text(t, encoding="utf-8", newline="")


def remove_if(t, prefix_re, indent):
    pattern = r"^" + (" " * indent) + r"if \(" + prefix_re + r"[^\n]*\) \{\n.*?^" + (" " * indent) + r"\}\n"
    return re.sub(pattern, "", t, flags=re.M | re.S)


def tidy(t):
    # Remove whole-line developer commentary without altering strings or regex literals.
    t = re.sub(r"^\s*//[^\n]*\n", "", t, flags=re.M)
    t = re.sub(r"^/\*\*.*?\*/\s*", "", t, flags=re.S)
    t = re.sub(r"^\s*console\.(?:log|warn|error|debug)\([^\n]*\);\s*$", "", t, flags=re.M)
    t = re.sub(r"[ \t]+$", "", t, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", t)


t = read("dom-translate-hook.js")
t = t[:t.index("function _paraMatchTag")]
t = t.replace("    tagUntranslatedSource(node, core);\n", "")
t = t[:t.index("    // FOURTH PASS")] + "}\n\n" + t[t.index("function processElementAttributes"):]
t = re.sub(r"^import .*?(?:gameStore|resolveDebugPath).*?;\n", "", t, flags=re.M)
t = re.sub(r"^        // Debug: tag parent element.*?^        return;", "        return;", t, flags=re.M | re.S)
t = re.sub(r"^        // TAG PARENT.*?^        return;", "        return;", t, flags=re.M | re.S)
t = re.sub(r"^            // Debug: tag parent with CSV key.*?^        \}", "        }", t, flags=re.M | re.S)
t = remove_if(t, r"typeof window !== 'undefined'", 8)
t = remove_if(t, r"key && typeof window !== 'undefined'", 16)
t = t.replace("    if (window.__WSR_DOM_TRANSLATE__ === false) return;\n", "")
t = t.replace("    if (node && node.parentElement && node.parentElement.closest('#wsr-ko-key-tip')) return;\n", "")
# Rendered-text key recovery belongs to the developer overlay, whose helpers are stripped.
t, n = re.subn(r"^    if \(isTargetScript\(core\) && node\.parentElement(?: && _overlayOn\(\))?\) \{\n.*?^    \}\n", "",
               t, flags=re.M | re.S)
assert n == 1, "Expected one rendered-text developer key recovery block"
assert "_keysForRenderedKorean" not in t
t += """
const _keyLookupRevision = 0;
if (enabled) {
    const start = () => {
        fullScan();
        let pending = [], queued = false;
        const flush = () => {
            queued = false;
            const batch = pending; pending = [];
            const seen = new Set();
            for (const m of batch) {
                for (const n of m.addedNodes || []) {
                    if (seen.has(n)) continue; seen.add(n);
                    if (n.nodeType === 1) scanNode(n);
                    else if (n.nodeType === 3) processTextNode(n);
                }
                if (seen.has(m.target)) continue;
                seen.add(m.target);
                if (m.type === 'characterData') processTextNode(m.target);
                else if (m.type === 'attributes') processElementAttributes(m.target);
            }
        };
        new MutationObserver(batch => {
            pending.push(...batch);
            if (!queued) { queued = true; requestAnimationFrame(flush); }
        }).observe(document.body, {childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['title','aria-label','placeholder']});
        setInterval(fullScan, 5000);
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
    else start();
}
"""
write("dom-translate-hook.js", tidy(t))

t = read("template-apply.js")
t = t[t.index("import {"):]
t = t[:t.index("const MAX_DUMP_SIZE")] + t[t.index("const TABLE_ROW_FIELDS"):]
t = t.replace("import { resolveDebugPath } from './wsr-debug-path.js';\n", "")
t = t[:t.index("function serializeForDump", t.index("        state[field] = result;", t.index("export function applyTemplatesToGameState")))]
t = re.sub(r"^    debugDumpQuarterlyIncomeCandidate\([^\n]*\);\n", "", t, flags=re.M)
t = re.sub(r"^    if \(t.length > 600\) \{\n.*?^    \}\n", "", t, flags=re.M | re.S)
t = re.sub(r"^function realKeysForKorean.*?(?=^function translateValue)", "", t, flags=re.M | re.S)
t = re.sub(r"^\s*(?:if \([^\n]*\) )?rememberCombinedKeys\([^\n]*\);\n", "\n", t, flags=re.M)
t = re.sub(r"^export function revertAppliedFields.*?(?=^export function applyTemplatesToGameState)", "", t, flags=re.M | re.S)
t = re.sub(r"^    if \(typeof window !== 'undefined'\) window\.__WSR_LAST_STATE__ = state;\n", "", t, flags=re.M)
t = re.sub(r"^    if \(typeof window !== 'undefined' && window\.__WSR_TEMPLATE_APPLY__ === false\) return;\n", "", t, flags=re.M)
t = remove_if(t, r"typeof window !== 'undefined'", 8)
t = remove_if(t, r"parts.length > 1 && typeof window !== 'undefined' && window\.__WSR_SENT_KEY__", 4)
assert "rememberCombinedKeys" not in t, "Developer key tracking call survived release stripping"
write("template-apply.js", tidy(t))

t = read("template-translate.js")
t = t[:t.index("// Live translation editing")] + t[t.index("const INDUSTRY_GROWTH_TRENDS"):]
t = remove_if(t, r"typeof window !== 'undefined' && result.source", 8)
write("template-translate.js", tidy(t))

for f in ["glossary-tooltip.js", "lang-base.js", "grammar-select.js"]:
    t = tidy(read(f))
    if f == "glossary-tooltip.js":
        t = t[:t.index("if (typeof window !== 'undefined') {", t.index("export function applyGlossaryTags"))]
        t = re.sub(r"`⚠ No definition for .*?`", "''", t)
    write(f, t)

# Follow the generated registry and language-module imports instead of a
# hardcoded language list. The game's own locale manager is supplied by WSR.
js_root = (S / "game_files/js").resolve()
source_root = (B / "game_files/js").resolve()
pending = [f for f in files if f.endswith(".js")]
seen = set()
import_re = re.compile(r"(?:\bfrom\s*|\bimport\s*)['\"](\.[^'\"]+\.js)['\"]")
while pending:
    rel = pending.pop()
    if rel in seen:
        continue
    seen.add(rel)
    for spec in import_re.findall(read(rel)):
        dest = (js_root / rel).parent.joinpath(spec).resolve()
        if not dest.is_relative_to(js_root):
            raise SystemExit(f"runtime import escapes js directory: {rel}: {spec}")
        dep = dest.relative_to(js_root).as_posix()
        if dep == "locale/localeManager.js":
            continue
        if not dest.exists():
            source = source_root / dep
            if not source.is_file():
                raise SystemExit(f"missing runtime dependency: {rel}: {spec}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        if dep not in files:
            files.append(dep)
        pending.append(dep)

# Developer metadata is unnecessary in the fixed translation dictionary.
p = S / "game_files/js/locale" / f"{prefix}-hook-data.json"
data = json.loads(p.read_text(encoding="utf-8"))
data = {k: v for k, v in data.items() if k in ["exact", "labels"]}
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
manifest = {f: hashlib.sha256((S / "game_files/js" / f).read_bytes()).hexdigest() for f in files}
(S / "payload_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("STAGED", len(files), f"production files for {args.locale}")
