import tempfile
import unittest
from pathlib import Path

from scripts.apply_fragment import apply_fragment, validate_fragment


class TestApplyFragment(unittest.TestCase):
    def test_validate_valid_fragment(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("# Comment line\n\nCONFIG_USER_NS=y\nCONFIG_TMPFS_XATTR=y\n")
            f.flush()
            opts = validate_fragment(Path(f.name))
            self.assertEqual(opts, ["CONFIG_USER_NS=y", "CONFIG_TMPFS_XATTR=y"])

    def test_validate_invalid_fragment(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("INVALID_LINE\nCONFIG_OK=y\n")
            f.flush()
            with self.assertRaises(ValueError):
                validate_fragment(Path(f.name))

    def test_apply_fragment_updates_and_appends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            frag = tmp / "test.fragment"
            frag.write_text("CONFIG_USER_NS=y\nCONFIG_NEW_OPTION=m\n")

            defconfig = tmp / "gki_defconfig"
            defconfig.write_text("CONFIG_USER_NS=n\nCONFIG_EXISTING=y\n")

            apply_fragment(frag, defconfig)
            content = defconfig.read_text().splitlines()

            self.assertIn("CONFIG_USER_NS=y", content)
            self.assertNotIn("CONFIG_USER_NS=n", content)
            self.assertIn("CONFIG_EXISTING=y", content)
            self.assertIn("CONFIG_NEW_OPTION=m", content)


if __name__ == "__main__":
    unittest.main()
