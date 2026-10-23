import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.setup_nomount import setup_nomount, wire_nomount


class TestSetupNomount(unittest.TestCase):
    def _make_tree(self, base: Path) -> tuple[Path, Path]:
        kernel_dir = base / "kernel"
        fs_dir = kernel_dir / "common" / "fs"
        fs_dir.mkdir(parents=True)
        (fs_dir / "Makefile").write_text("obj-y += existing/\n")
        (fs_dir / "Kconfig").write_text('menu "File systems"\nendmenu\n')
        defconfig = kernel_dir / "common" / "arch" / "arm64" / "configs" / "gki_defconfig"
        defconfig.parent.mkdir(parents=True)
        defconfig.write_text("CONFIG_NOMOUNT=n\nCONFIG_EXISTING=y\n")
        source_dir = kernel_dir / "NoMount" / "kernel" / "src"
        source_dir.mkdir(parents=True)
        (source_dir / "Kconfig").write_text('config NOMOUNT\n\ttristate "NoMount"\n')
        (source_dir / "Makefile").write_text("obj-$(CONFIG_NOMOUNT) += nomount.o\n")
        return kernel_dir, source_dir

    def test_wire_nomount(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel_dir, source_dir = self._make_tree(Path(tmpdir))
            fs_dir = kernel_dir / "common" / "fs"

            wire_nomount(kernel_dir, source_dir)

            link = fs_dir / "nomount"
            self.assertTrue(link.is_symlink())
            self.assertEqual(Path(link.readlink()), Path("../../NoMount/kernel/src"))
            self.assertIn("obj-$(CONFIG_NOMOUNT) += nomount/", (fs_dir / "Makefile").read_text())
            kconfig = (fs_dir / "Kconfig").read_text()
            self.assertIn('source "fs/nomount/Kconfig"', kconfig)
            self.assertLess(kconfig.index('source "fs/nomount/Kconfig"'), kconfig.index("endmenu"))
            defconfig = (kernel_dir / "common" / "arch" / "arm64" / "configs" / "gki_defconfig").read_text()
            self.assertIn("CONFIG_NOMOUNT=y", defconfig)
            self.assertIn("CONFIG_KEYS=y", defconfig)
            self.assertNotIn("CONFIG_NOMOUNT=n", defconfig)

    def test_wire_nomount_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel_dir, source_dir = self._make_tree(Path(tmpdir))
            fs_dir = kernel_dir / "common" / "fs"

            wire_nomount(kernel_dir, source_dir)
            wire_nomount(kernel_dir, source_dir)

            self.assertEqual((fs_dir / "Makefile").read_text().count("CONFIG_NOMOUNT"), 1)
            self.assertEqual((fs_dir / "Kconfig").read_text().count('source "fs/nomount/Kconfig"'), 1)

    def test_wire_nomount_replaces_not_set_comment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel_dir, source_dir = self._make_tree(Path(tmpdir))
            defconfig = kernel_dir / "common" / "arch" / "arm64" / "configs" / "gki_defconfig"
            defconfig.write_text("# CONFIG_NOMOUNT is not set\nCONFIG_EXISTING=y\n")

            wire_nomount(kernel_dir, source_dir)

            content = defconfig.read_text()
            self.assertIn("CONFIG_NOMOUNT=y", content)
            self.assertNotIn("# CONFIG_NOMOUNT is not set", content)

    def test_setup_nomount_uses_local_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            kernel_dir, _ = self._make_tree(base)
            repo_dir = kernel_dir / "NoMount"
            subprocess.run(["git", "init", "-q", str(repo_dir)], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "commit", "-qm", "init"], check=True)
            expected = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            sha = setup_nomount(kernel_dir)

            self.assertEqual(sha, expected)
            self.assertTrue((kernel_dir / "common" / "fs" / "nomount").is_symlink())

    def test_setup_nomount_cloned_no_checkout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            kernel_dir, _ = self._make_tree(base)
            repo_dir = kernel_dir / "NoMount"
            subprocess.run(["git", "init", "-q", str(repo_dir)], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "commit", "-qm", "init"], check=True)
            expected = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            # Simulate --no-checkout by removing working directory files while keeping .git
            for item in repo_dir.iterdir():
                if item.name != ".git":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

            sha = setup_nomount(kernel_dir)
            self.assertEqual(sha, expected)
            self.assertTrue((repo_dir / "kernel" / "src" / "Kconfig").is_file())
            self.assertTrue((kernel_dir / "common" / "fs" / "nomount").is_symlink())

    def test_wire_nomount_flat_tree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            kernel_dir = base / "kernel"
            fs_dir = kernel_dir / "fs"
            fs_dir.mkdir(parents=True)
            (fs_dir / "Makefile").write_text("obj-y += existing/\n")
            (fs_dir / "Kconfig").write_text('menu "File systems"\nendmenu\n')
            defconfig = kernel_dir / "arch" / "arm64" / "configs" / "gki_defconfig"
            defconfig.parent.mkdir(parents=True)
            defconfig.write_text("CONFIG_NOMOUNT=n\n")
            source_dir = kernel_dir / "NoMount" / "kernel" / "src"
            source_dir.mkdir(parents=True)
            (source_dir / "Kconfig").write_text('config NOMOUNT\n\ttristate "NoMount"\n')

            wire_nomount(kernel_dir, source_dir)

            self.assertTrue((fs_dir / "nomount").is_symlink())
            self.assertIn("CONFIG_NOMOUNT=y", defconfig.read_text())
            self.assertIn("CONFIG_KEYS=y", defconfig.read_text())


if __name__ == "__main__":
    unittest.main()
