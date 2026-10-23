import tempfile
import unittest
from pathlib import Path

from scripts.apply_fmrd import (
    apply_fmrd,
    apply_fmrd_defconfig,
    find_common_dir,
    resolve_patch_file,
    wire_fmrd,
)


class TestApplyFmrd(unittest.TestCase):
    def test_apply_fmrd_defconfig_new(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("CONFIG_EXISTING=y\n")
            f.flush()
            defconfig = Path(f.name)
            apply_fmrd_defconfig(defconfig)
            content = defconfig.read_text().splitlines()
            self.assertIn("CONFIG_FMRD=y", content)

    def test_apply_fmrd_defconfig_replace_is_not_set(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("CONFIG_EXISTING=y\n# CONFIG_FMRD is not set\n")
            f.flush()
            defconfig = Path(f.name)
            apply_fmrd_defconfig(defconfig)
            content = defconfig.read_text().splitlines()
            self.assertIn("CONFIG_FMRD=y", content)
            self.assertNotIn("# CONFIG_FMRD is not set", content)

    def test_find_common_dir_nested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "common" / "include" / "linux").mkdir(parents=True)
            res = find_common_dir(base)
            self.assertEqual(res, base / "common")

    def test_find_common_dir_flat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "include" / "linux").mkdir(parents=True)
            res = find_common_dir(base)
            self.assertEqual(res, base)

    def test_find_common_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with self.assertRaises(FileNotFoundError):
                find_common_dir(base)

    def test_resolve_patch_file_default(self):
        patch = resolve_patch_file(None)
        self.assertTrue(patch.is_file())
        self.assertTrue(patch.name.endswith(".patch"))

    def test_resolve_patch_file_missing(self):
        with self.assertRaises(FileNotFoundError):
            resolve_patch_file(Path("/nonexistent/fmrd.patch"))

    def test_apply_fmrd_mock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            common = base / "common"
            (common / "include" / "linux").mkdir(parents=True)
            defconfig_dir = common / "arch" / "arm64" / "configs"
            defconfig_dir.mkdir(parents=True)
            defconfig = defconfig_dir / "gki_defconfig"
            defconfig.write_text("CONFIG_TEST=y\n")

            target_file = common / "test.c"
            target_file.write_text("line1\nline2\n")

            patch_file = base / "sample.patch"
            patch_file.write_text(
                "--- a/test.c\n+++ b/test.c\n@@ -1,2 +1,3 @@\n line1\n+added_line\n line2\n"
            )

            ver = apply_fmrd(base, patch_file=patch_file)
            self.assertEqual(ver, "1.0.0")
            self.assertIn("added_line", target_file.read_text())
            self.assertIn("CONFIG_FMRD=y", defconfig.read_text())

    def test_wire_fmrd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            fs_dir = base / "fs"
            fs_dir.mkdir(parents=True)
            makefile = fs_dir / "Makefile"
            makefile.write_text("obj-y += foo/\n")
            kconfig = fs_dir / "Kconfig"
            kconfig.write_text('menu "File systems"\nendmenu\n')

            wire_fmrd(base)

            self.assertIn("obj-$(CONFIG_FMRD) += fmrd.o", makefile.read_text())
            self.assertIn("config FMRD", kconfig.read_text())
            self.assertLess(kconfig.read_text().index("config FMRD"), kconfig.read_text().index("endmenu"))

            # Idempotency check
            wire_fmrd(base)
            self.assertEqual(makefile.read_text().count("CONFIG_FMRD"), 1)
            self.assertEqual(kconfig.read_text().count("config FMRD"), 1)


if __name__ == "__main__":
    unittest.main()
