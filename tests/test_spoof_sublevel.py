import subprocess
import sys
import unittest

from scripts.spoof_sublevel import build_version, validate_sublevel


class TestSpoofSublevel(unittest.TestCase):
    def test_validate_sublevel_accepts_digits(self):
        self.assertEqual(validate_sublevel("113"), 113)
        self.assertEqual(validate_sublevel(" 113 "), 113)

    def test_validate_sublevel_rejects_empty_value(self):
        with self.assertRaises(ValueError):
            validate_sublevel("")
        with self.assertRaises(ValueError):
            validate_sublevel("   ")

    def test_validate_sublevel_rejects_non_numeric_value(self):
        for value in ("113x", "-1", "6.12.113"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_sublevel(value)

    def test_build_version_with_brand(self):
        self.assertEqual(
            build_version("6.12", 113, "android16", "5", "WantRelax"),
            "6.12.113-android16-5-WantRelax",
        )

    def test_build_version_without_brand(self):
        self.assertEqual(
            build_version("6.12", 113, "android16", "5"),
            "6.12.113-android16-5",
        )

    def test_cli_prints_spoofed_version(self):
        result = subprocess.run(
            [
                sys.executable,
                "scripts/spoof_sublevel.py",
                "--kernel-part",
                "6.12",
                "--sublevel",
                "113",
                "--android-part",
                "android16",
                "--kmi",
                "5",
                "--brand",
                "WantRelax",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "6.12.113-android16-5-WantRelax")


if __name__ == "__main__":
    unittest.main()
