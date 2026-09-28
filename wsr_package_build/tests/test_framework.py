"""Integration checks use disposable kits, never the installed game.

Run: python -m unittest discover -s tests -v
Node is required for runtime and staged player checks; no third-party Python
dependencies are needed. The full repository is required for release tests.
"""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]
RELEASE = KIT.parent / "dist_build"
if not RELEASE.is_dir():
    RELEASE = KIT / "release_tools"
sys.path.insert(0, str(KIT / "pipeline_tools"))
from grammar_checks import selector_problems, without_selectors
from locale_framework import token_problems


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames), list(reader)


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class GrammarChecks(unittest.TestCase):
    def test_selectors(self):
        valid = "{{@ASSET2.agreement|m_sg=nouveau|f_sg=nouvelle|other=moderne}}"
        self.assertEqual(selector_problems(valid), [])
        for bad in ["{{@COUNT.plural|one=share}}", "{{@ASSET.gender|f=a|f=b|other=c}}",
                    "{{@COUNT0.plural|other=shares}}", "{{@ASSET.case|other=x}}",
                    "{{@ASSET.gender|f={a|b}|other=c}}"]:
            self.assertTrue(selector_problems(bad), bad)
        self.assertEqual(token_problems("@ASSET and @ASSET", without_selectors(valid))[0], [])
        self.assertTrue(token_problems("@ASSET", without_selectors(valid))[0])
        self.assertTrue(token_problems("@ASSET", "@ASSET0")[0])


class DisposableKit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wsr-framework-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kit = self.root / "kit"
        self.kit.mkdir()
        for name in ("source_data", "locales", "reference_data", "pipeline_tools", "game_files"):
            shutil.copytree(KIT / name, self.kit / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for path in KIT.iterdir():
            if path.is_file() and path.suffix in {".py", ".json", ".csv", ".md"}:
                shutil.copy2(path, self.kit / path.name)

    def run_python(self, *args, ok=True):
        result = subprocess.run([sys.executable, "-B", *map(str, args)], cwd=self.kit,
                                capture_output=True, text=True, encoding="utf-8",
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def runtime(self, directory):
        result = subprocess.run(["node", "--experimental-vm-modules", str(KIT / "tests/runtime.test.cjs"),
                                 str(directory)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_each_locale_and_player_payload(self):
        for locale in ("ko-KR", "fr-FR", "ja-JP"):
            self.run_python("pipeline.py", "build", "--locale", locale)
            prefix = locale.split('-')[0]
            hooks = json.loads((self.kit / f"game_files/js/locale/{prefix}-hook-data.json").read_text(encoding="utf-8"))
            self.assertGreater(len(hooks["keys"]), 0, "untranslated locales need editor source keys")
            if not RELEASE.is_dir():
                continue
            stage = self.root / locale
            self.run_python(RELEASE / "build_user_release.py", "--source", self.kit,
                            "--output", stage, "--locale", locale)
            self.runtime(stage / "game_files/js")
            for file in (stage / "game_files/js").rglob("*.js"):
                result = subprocess.run(["node", "--check", str(file)], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
        self.runtime(self.kit / "game_files/js")

    def test_source_independent_of_korean_locale(self):
        # This path is inside the disposable kit created in setUp.
        shutil.rmtree(self.kit / "locales/ko-KR")
        profiles_file = self.kit / "locale_profiles.json"
        profiles = json.loads(profiles_file.read_text(encoding="utf-8"))
        del profiles["ko-KR"]
        profiles_file.write_text(json.dumps(profiles), encoding="utf-8")
        for file in (self.kit / "game_files/js/locale").glob("ko-*.json"):
            file.unlink()
        self.run_python("pipeline.py", "check", "--locale", "fr-FR")
        self.run_python("pipeline.py", "build", "--locale", "fr-FR")

    def test_refresh_preserves_existing_locale_targets(self):
        for code in ("ko-KR", "fr-FR", "ja-JP"):
            folder = self.kit / "locales" / code
            def targets():
                return {row["Key"]: {key: value for key, value in row.items() if key.startswith("Target (")}
                        for file in folder.glob("WSR_translation_*.csv") for row in read_csv(file)[1]}
            before = targets()
            self.run_python("pipeline.py", "init-locale", "--locale", code)
            self.assertEqual(targets(), before, code)

    def test_key_migration_updates_source_and_every_locale(self):
        source_file = self.kit / "source_data/WSR_translation_all.csv"
        old = read_csv(source_file)[1][0]["Key"]
        new = "framework_test_renamed_key"
        migration_file = self.kit / "key_migrations.csv"
        fields, rows = read_csv(migration_file)
        rows.append({"Old Key": old, "New Key": new, "Reason": "test shared rename"})
        write_csv(migration_file, fields, rows)
        original_targets = {}
        for code in ("ko-KR", "fr-FR", "ja-JP"):
            original_targets[code] = next(r for r in read_csv(self.kit / "locales" / code / source_file.name)[1] if r["Key"] == old)
        self.run_python("pipeline_tools/manage_keys.py", "--write")
        self.assertIn(new, {r["Key"] for r in read_csv(source_file)[1]})
        for code, original in original_targets.items():
            current = next(r for r in read_csv(self.kit / "locales" / code / source_file.name)[1] if r["Key"] == new)
            self.assertEqual({**original, "Key": new}, current)

    def test_rename_key_command_moves_row_to_its_prefix_file(self):
        old = read_csv(self.kit / "source_data/WSR_translation_all.csv")[1][0]["Key"]
        existing = read_csv(self.kit / "source_data/WSR_translation_mainui.csv")[1][0]["Key"]
        new = "popup_FrameworkTestRenamed"
        self.run_python("pipeline.py", "rename-key", old, existing, ok=False)
        self.run_python("pipeline.py", "rename-key", old, "bad key!", ok=False)
        before = next(r for r in read_csv(self.kit / "locales/ko-KR/WSR_translation_all.csv")[1] if r["Key"] == old)
        self.run_python("pipeline.py", "rename-key", old, new)
        self.assertEqual(read_csv(self.kit / "key_migrations.csv")[1][-1]["New Key"], new)
        for code in ("ko-KR", "fr-FR", "ja-JP"):
            folder = self.kit / "locales" / code
            self.assertNotIn(old, {r["Key"] for r in read_csv(folder / "WSR_translation_all.csv")[1]})
            self.assertIn(new, {r["Key"] for r in read_csv(folder / "WSR_translation_mainui.csv")[1]})
        after = next(r for r in read_csv(self.kit / "locales/ko-KR/WSR_translation_mainui.csv")[1] if r["Key"] == new)
        self.assertEqual(after["Target (KO)"], before["Target (KO)"])
        self.run_python("pipeline.py", "check")

    def test_refresh_preserves_work_and_tracks_source_changes(self):
        name = "WSR_translation_all.csv"
        translated = self.kit / "locales/fr-FR" / name
        source = self.kit / "source_data" / name
        fields, rows = read_csv(translated)
        key = rows[0]["Key"]
        old_source = rows[0]["Source (EN)"]
        fields.append("Notes")
        for row in rows:
            row["Notes"] = ""
        rows[0].update({"Target (FR)": "Texte conservé", "Notes": "Translator note"})
        write_csv(translated, fields, rows)
        sf, sr = read_csv(source)
        next(row for row in sr if row["Key"] == key)["Source (EN)"] += " changed"
        write_csv(source, sf, sr)
        var_path = self.kit / "locales/fr-FR/vars/VAR_entity_names.csv"
        vf, vr = read_csv(var_path)
        vf.append("form_GENITIVE")
        for row in vr:
            row["form_GENITIVE"] = ""
        vr[0].update(target="banque", gender="f", number="sg", form_GENITIVE="de banque")
        write_csv(var_path, vf, vr)
        self.run_python("pipeline.py", "init-locale", "--locale", "fr-FR")
        current = next(r for r in read_csv(translated)[1] if r["Key"] == key)
        self.assertEqual(current["Source (EN)"], old_source)
        self.assertEqual(current["Target (FR)"], "Texte conservé")
        self.assertEqual(current["Notes"], "Translator note")
        self.assertEqual(read_csv(var_path)[1][0]["form_GENITIVE"], "de banque")
        result = self.run_python("pipeline.py", "build", "--locale", "fr-FR")
        self.assertIn("English source changed", result.stdout)
        data = json.loads((self.kit / "game_files/js/locale/fr-hook-data.json").read_text(encoding="utf-8"))
        self.assertNotIn("Texte conservé", data["exact"].values())
        write_csv(source, sf, [r for r in sr if r["Key"] != key])
        self.run_python("pipeline.py", "init-locale", "--locale", "fr-FR")
        archived = read_csv(self.kit / "locales/fr-FR/retired_translations.csv")[1]
        self.assertTrue(any(r["Key"] == key and r["Notes"] == "Translator note" for r in archived))

    def test_regional_locales_and_custom_module_dependencies(self):
        profiles_file = self.kit / "locale_profiles.json"
        profiles = json.loads(profiles_file.read_text(encoding="utf-8"))
        for region in ("BR", "PT"):
            profiles[f"pt-{region}"] = {"name": f"Português ({region})", "target_column": "Target (PT)",
                "morphology": "pt", "runtime_module": "lang-pt.js", "runtime_export": f"{region}_RULES"}
        profiles_file.write_text(json.dumps(profiles), encoding="utf-8")
        js = self.kit / "game_files/js"
        (js / "pt-months.js").write_text("export const month = 'dezembro';\n", encoding="utf-8")
        (js / "lang-pt.js").write_text(
            "import { BASE_RULES } from './lang-base.js';\nimport { month } from './pt-months.js';\n"
            "export const BR_RULES = {...BASE_RULES, month:()=>month+'-BR'};\n"
            "export const PT_RULES = {...BASE_RULES, month:()=>month+'-PT'};\n", encoding="utf-8")
        for code in ("pt-BR", "pt-PT"):
            self.run_python("pipeline.py", "init-locale", "--locale", code)
            self.run_python("pipeline.py", "build", "--locale", code)
            self.assertTrue((js / "locale" / f"{code}-templates.json").exists())
            if RELEASE.is_dir():
                stage = self.root / code
                self.run_python(RELEASE / "build_user_release.py", "--source", self.kit,
                                "--output", stage, "--locale", code)
                self.assertTrue((stage / "game_files/js/pt-months.js").exists())
                self.runtime(stage / "game_files/js")
        self.runtime(js)
        profiles["pt-PT"]["data_prefix"] = "pt-BR"
        profiles_file.write_text(json.dumps(profiles), encoding="utf-8")
        self.run_python("pipeline.py", "check", "--locale", "pt-PT", ok=False)

    def test_invalid_grammar_blocks_release_before_overwriting_output(self):
        path = self.kit / "locales/fr-FR/WSR_translation_all.csv"
        fields, rows = read_csv(path)
        rows[0]["Target (FR)"] = "{{@ASSET.gender|f=nouvelle}}"
        write_csv(path, fields, rows)
        self.run_python("pipeline.py", "check", "--locale", "fr-FR", ok=False)
        if not RELEASE.is_dir():
            return
        stage = self.root / "release"
        (stage / "game_files").mkdir(parents=True)
        sentinel = stage / "game_files/existing.txt"
        sentinel.write_text("keep", encoding="utf-8")
        self.run_python(RELEASE / "build_user_release.py", "--source", self.kit,
                        "--output", stage, "--locale", "fr-FR", ok=False)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_translator_kit_can_build_player_without_repository(self):
        builder = RELEASE / "build_translator_release.py"
        if not builder.exists():
            self.skipTest("translator staging builder is available in the full repository")
        output = self.root / "translator"
        self.run_python(builder, "--source", self.kit, "--output", output)
        for relative in ("source_data/WSR_translation_all.csv", "MULTILINGUAL.md",
                         "build_player.bat", "release_tools/build_user_release.py"):
            self.assertTrue((output / relative).is_file(), relative)
        stage = self.root / "player-from-kit"
        self.run_python(output / "release_tools/build_user_release.py", "--source", output,
                        "--output", stage, "--locale", "fr-FR")
        self.runtime(stage / "game_files/js")


if __name__ == "__main__":
    unittest.main()
