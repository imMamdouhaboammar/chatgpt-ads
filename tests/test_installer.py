from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name == "nt", "POSIX installer remains explicitly unsupported on Windows")
class InstallerTests(unittest.TestCase):
    def run_installer(self, *args, home):
        env = {**os.environ, "HOME": str(home)}
        return subprocess.run(["bash", str(ROOT / "install.sh"), *map(str, args)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)

    def test_dry_run_does_not_create_target(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / "custom/chatgpt-ads"
            result = self.run_installer("--target", target, "--dry-run", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(target.exists())

    def test_install_uses_runtime_allowlist_and_smoke_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / "custom/chatgpt-ads"
            result = self.run_installer("--target", target, home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((target / ".chatgpt-ads-install.json").is_file())
            self.assertTrue((target / "chatgpt_ads_brain/openai_ads.py").is_file())
            self.assertTrue((target / "tests").is_dir())
            self.assertFalse((target / ".git").exists())
            smoke = subprocess.run(["python3", "-m", "chatgpt_ads_brain", "--help"], cwd=target, capture_output=True, text=True, check=False)
            self.assertEqual(smoke.returncode, 0, smoke.stderr)
            validate = subprocess.run(["python3", "-m", "chatgpt_ads_brain", "validate"], cwd=target, capture_output=True, text=True, check=False)
            self.assertEqual(validate.returncode, 0, validate.stderr)

    def test_existing_target_requires_upgrade_or_force_and_is_backed_up(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / "custom/chatgpt-ads"
            target.mkdir(parents=True)
            (target / "user-file.txt").write_text("preserve", encoding="utf-8")
            refused = self.run_installer("--target", target, home=home)
            self.assertNotEqual(refused.returncode, 0)
            upgraded = self.run_installer("--target", target, "--upgrade", home=home)
            self.assertNotEqual(upgraded.returncode, 0)
            forced = self.run_installer("--target", target, "--force", home=home)
            self.assertEqual(forced.returncode, 0, forced.stderr)
            backups = list(target.parent.glob("chatgpt-ads.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "user-file.txt").read_text(), "preserve")

    def test_target_overlap_and_normalized_home_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for target in (ROOT / "nested-install", ROOT.parent, home):
                with self.subTest(target=str(target)):
                    result = self.run_installer("--target", target, "--dry-run", home=home)
                    self.assertNotEqual(result.returncode, 0, result.stderr)

    def test_uninstall_preserves_atomic_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / "custom/chatgpt-ads"
            self.assertEqual(self.run_installer("--target", target, home=home).returncode, 0)
            removed = self.run_installer("--target", target, "--uninstall", home=home)
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse(target.exists())
            self.assertEqual(len(list(target.parent.glob("chatgpt-ads.removed.*"))), 1)


if __name__ == "__main__":
    unittest.main()
