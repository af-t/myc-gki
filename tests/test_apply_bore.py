import tempfile
import unittest
from pathlib import Path

from scripts.apply_bore import (
    apply_bore,
    apply_bore_defconfig,
    find_common_dir,
    resolve_patch_file,
)


class TestApplyBore(unittest.TestCase):
    def test_apply_bore_defconfig_new(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("CONFIG_EXISTING=y\n")
            f.flush()
            defconfig = Path(f.name)
            apply_bore_defconfig(defconfig)
            content = defconfig.read_text().splitlines()
            self.assertIn("CONFIG_SCHED_BORE=y", content)

    def test_apply_bore_defconfig_replace_is_not_set(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("CONFIG_EXISTING=y\n# CONFIG_SCHED_BORE is not set\n")
            f.flush()
            defconfig = Path(f.name)
            apply_bore_defconfig(defconfig)
            content = defconfig.read_text().splitlines()
            self.assertIn("CONFIG_SCHED_BORE=y", content)
            self.assertNotIn("# CONFIG_SCHED_BORE is not set", content)

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
            resolve_patch_file(Path("/nonexistent/bore.patch"))

    def test_apply_bore_mock(self):
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

            ver = apply_bore(base, patch_file=patch_file)
            self.assertEqual(ver, "7.0.0")
            self.assertIn("added_line", target_file.read_text())
            self.assertIn("CONFIG_SCHED_BORE=y", defconfig.read_text())


if __name__ == "__main__":
    unittest.main()
