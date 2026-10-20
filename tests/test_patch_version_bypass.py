import tempfile
import unittest
from pathlib import Path

from scripts.patch_version_bypass import patch_version_bypass


class TestPatchVersionBypass(unittest.TestCase):
    def test_patch_version_c(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "kernel" / "module" / "version.c"
            target.parent.mkdir(parents=True)
            target.write_text(
                "static int check_version(...) {\n"
                "bad_version:\n"
                "\tpr_warn(\"bad version\");\n"
                "\treturn 0;\n"
                "}\n"
            )
            patch_version_bypass(base)
            content = target.read_text()
            self.assertIn("return 1;", content)
            self.assertNotIn("return 0;", content)

    def test_patch_fallback_module_c(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "kernel" / "module.c"
            target.parent.mkdir(parents=True)
            target.write_text(
                "bad_version:\n"
                "\treturn 0;\n"
            )
            patch_version_bypass(base)
            content = target.read_text()
            self.assertIn("return 1;", content)

    def test_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "kernel" / "module" / "version.c"
            target.parent.mkdir(parents=True)
            target.write_text(
                "bad_version:\n"
                "\tpr_warn(\"bad version\");\n"
                "\treturn 1;\n"
            )

            patch_version_bypass(base)

            self.assertIn("return 1;", target.read_text())

    def test_missing_target_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with self.assertRaises(FileNotFoundError):
                patch_version_bypass(base)


if __name__ == "__main__":
    unittest.main()
