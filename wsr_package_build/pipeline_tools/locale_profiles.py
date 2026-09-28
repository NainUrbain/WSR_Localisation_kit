"""Validated locale profiles and generated ES-module registry.

One registration controls data filenames, language rules and packaging.
Regional locales must use distinct data_prefix values.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_NAME = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*\Z")
LOCALE_CODE = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z")


def load_profiles():
    profiles = json.loads((ROOT / "locale_profiles.json").read_text(encoding="utf-8"))
    prefixes = set()
    codes = set()
    for code, profile in profiles.items():
        if not LOCALE_CODE.fullmatch(code) or code.casefold() in codes:
            raise ValueError(f"invalid locale code: {code!r}")
        codes.add(code.casefold())
        prefix = profile.get("data_prefix", code)
        if not SAFE_NAME.fullmatch(prefix) or prefix.casefold() in prefixes:
            raise ValueError(f"invalid or duplicate data_prefix: {prefix!r}")
        prefixes.add(prefix.casefold())
        profile["data_prefix"] = prefix
        if not re.fullmatch(r"Target \([A-Za-z0-9_-]+\)", profile.get("target_column", "")):
            raise ValueError(f"{code}: target_column must have the form Target (XX)")
        morphology = profile.get("morphology", "")
        if morphology and not SAFE_NAME.fullmatch(morphology):
            raise ValueError(f"{code}: invalid morphology")
        module = profile.get("runtime_module", f"lang-{morphology}.js" if morphology else "lang-base.js")
        export = profile.get("runtime_export", f"{morphology.upper()}_RULES" if morphology else "BASE_RULES")
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.js", module):
            raise ValueError(f"{code}: runtime_module must be a JS filename")
        if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", export):
            raise ValueError(f"{code}: invalid runtime_export")
        if not (ROOT / "game_files" / "js" / module).is_file():
            raise ValueError(f"{code}: missing language module {module}")
        profile.update(runtime_module=module, runtime_export=export)
    return profiles


def write_registry(output_dir, locales=None):
    profiles = load_profiles()
    selected = list(profiles) if locales is None else list(locales)
    lines = ["// Generated from locale_profiles.json. Do not edit.\n"]
    refs = {}
    for code in selected:
        profile = profiles[code]
        pair = (profile["runtime_module"], profile["runtime_export"])
        if pair not in refs:
            refs[pair] = f"rules{len(refs)}"
            lines.append(f"import {{ {pair[1]} as {refs[pair]} }} from './{pair[0]}';\n")
    lines.append("export const LANGUAGE_RULES = {\n")
    for code in selected:
        p = profiles[code]
        lines.append(f"    {json.dumps(code)}: {refs[p['runtime_module'], p['runtime_export']]},\n")
    lines.append("};\nexport const LOCALE_PROFILES = " + json.dumps(
        {code: {"data_prefix": profiles[code]["data_prefix"]} for code in selected}, indent=2
    ) + ";\n")
    lines.append("export function localeDataFile(locale, suffix) {\n"
                 "    const profile = LOCALE_PROFILES[locale];\n"
                 "    return profile ? `${profile.data_prefix}-${suffix}` : null;\n}\n")
    path = Path(output_dir) / "locale-registry.js"
    path.write_text("".join(lines), encoding="utf-8", newline="\n")
    return str(path)
