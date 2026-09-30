"""Workshop source selection must never package unverified local game edits."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dist_build"))
from build_workshop_release import build, original_bytes, replace_function, replace_once


class WorkshopBuilderSafety(unittest.TestCase):
    def test_only_matching_original_or_backup_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp)
            entry = {"path": "js/api.js", "original_sha256": hashlib.sha256(b"original").hexdigest()}
            (app / "js").mkdir()
            (app / entry["path"]).write_bytes(b"unrelated user edits")
            with self.assertRaisesRegex(ValueError, "No supported original"):
                original_bytes(app, entry)
            backup = app / "wsr-kr-developer-backup" / entry["path"]
            backup.parent.mkdir(parents=True)
            backup.write_bytes(b"original")
            self.assertEqual(original_bytes(app, entry), (b"original", str(backup)))
            self.assertEqual((app / entry["path"]).read_bytes(), b"unrelated user edits")
            backup.write_bytes(b"modified backup")
            with self.assertRaises(ValueError):
                original_bytes(app, entry)

    def test_output_cannot_overlap_game_or_existing_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = root / "game/resources/app"
            app.mkdir(parents=True)
            for output in (app, app / "mod", root / "game"):
                with self.assertRaisesRegex(ValueError, "overlap"):
                    build(app, output, "ko-KR")
            output = root / "existing-release"
            output.mkdir()
            item_id = output / ".wsrmod-id"
            item_id.write_text("12345")
            with self.assertRaisesRegex(ValueError, "already exists"):
                build(app, output, "ko-KR")
            self.assertEqual(item_id.read_text(), "12345")

    def test_runtime_adapters_fail_if_source_anchors_drift(self):
        with self.assertRaises(ValueError):
            replace_once("x x", "x", "y")
        with self.assertRaises(ValueError):
            replace_function("function renamed() {}", "readJsonNear", "")


if __name__ == "__main__":
    unittest.main()
