"""Installer regressions using small synthetic game files."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
PLAYER = KIT.parent / "dist_build/install_patch_dist.py"
if not PLAYER.exists():
    PLAYER = KIT / "release_tools/install_patch_dist.py"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest(original, patched):
    return {"files": [{"path": "js/api.js", "original_sha256": digest(original),
        "patched_sha256": digest(patched), "hunks": [{"start_line": 0, "delete_count": 1,
        "original_sha256": digest(original), "new_text": patched.decode()}]}]}


class InstallerTests(unittest.TestCase):
    def exercise(self, callback):
        for module_file in (KIT / "install_patch.py", PLAYER):
            if not module_file.exists():
                continue
            with self.subTest(installer=module_file.name), tempfile.TemporaryDirectory(prefix="wsr-installer-test-") as temp:
                if module_file == PLAYER:
                    # The player installer reads its manifests beside itself at import
                    # time; they only exist in a staged build, so stage a stub copy.
                    stub = Path(temp) / "player"
                    stub.mkdir()
                    for name in ("install_patch_dist.py", "patcher_core.py", "patch_manifest.json"):
                        shutil.copy2(PLAYER.parent / name, stub / name)
                    (stub / "payload_manifest.json").write_text("{}\n", encoding="utf-8")
                    module_file = stub / PLAYER.name
                spec = importlib.util.spec_from_file_location("test_installer_module", module_file)
                installer = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(installer)
                installer.MODE = "player"
                installer.BACKUP_NAME = "test-backup"
                installer.PAYLOAD = {}
                app = Path(temp)
                (app / "js").mkdir()
                (app / "js/api.js").write_bytes(b"game-v1\n")
                installer.PATCHES = manifest(b"game-v1\n", b"patched-v1\n")
                with contextlib.redirect_stdout(io.StringIO()):
                    callback(installer, app)

    def test_supported_update_refreshes_original_backup(self):
        def scenario(installer, app):
            installer.install(app)
            installer.uninstall(app)
            (app / "js/api.js").write_bytes(b"game-v2\n")
            installer.PATCHES = manifest(b"game-v2\n", b"patched-v2\n")
            installer.install(app)
            installer.uninstall(app)
            self.assertEqual((app / "js/api.js").read_bytes(), b"game-v2\n")
        self.exercise(scenario)

    def test_uninstall_rejects_changed_game_and_damaged_backup(self):
        def scenario(installer, app):
            installer.install(app)
            file = app / "js/api.js"
            file.write_bytes(b"unexpected-Steam-update\n")
            with self.assertRaises(RuntimeError):
                installer.uninstall(app)
            self.assertEqual(file.read_bytes(), b"unexpected-Steam-update\n")
            file.write_bytes(b"patched-v1\n")
            (app / installer.BACKUP_NAME / "js/api.js").write_bytes(b"damaged\n")
            with self.assertRaises(RuntimeError):
                installer.uninstall(app)
            self.assertEqual(file.read_bytes(), b"patched-v1\n")
        self.exercise(scenario)

    def test_unknown_game_is_not_backed_up_or_modified(self):
        def scenario(installer, app):
            (app / "js/api.js").write_bytes(b"unsupported\n")
            with self.assertRaises(RuntimeError):
                installer.install(app)
            self.assertFalse((app / installer.BACKUP_NAME).exists())
            self.assertEqual((app / "js/api.js").read_bytes(), b"unsupported\n")
        self.exercise(scenario)


if __name__ == "__main__":
    unittest.main()
