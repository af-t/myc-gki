import tempfile
import unittest
from pathlib import Path

from scripts.remove_protected_exports import remove_protected_exports


class TestRemoveProtectedExports(unittest.TestCase):
    def test_remove_protected_exports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel_dir = Path(tmpdir)
            common = kernel_dir / "common"
            android = common / "android"
            android.mkdir(parents=True)

            (android / "abi_gki_protected_exports_aarch64").write_text("dummy")
            (android / "abi_gki_protected_exports_x86_64").write_text("dummy")

            build_bazel = common / "BUILD.bazel"
            build_bazel.write_text(
                'kernel_build(\n'
                '    name = "kernel_aarch64",\n'
                '    "protected_exports_list": "android/abi_gki_protected_exports_aarch64",\n'
                '    protected_module_names_list = ":gki_aarch64_protected_module_names",\n'
                ')\n'
            )

            modules_bzl = common / "modules.bzl"
            modules_bzl.write_text(
                'protected_modules = [\n'
                '    "foo.ko",\n'
                '    "bar.ko",\n'
                ']\n'
            )

            remove_protected_exports(kernel_dir)

            self.assertEqual(list(android.glob("abi_gki_protected_exports_*")), [])
            bazel_content = build_bazel.read_text()
            self.assertNotIn("protected_exports_list", bazel_content)
            self.assertNotIn("protected_module_names_list", bazel_content)
            bzl_content = modules_bzl.read_text()
            self.assertIn("protected_modules = []", bzl_content)
            self.assertNotIn("foo.ko", bzl_content)

    def test_raises_if_protected_module_names_list_remains(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel_dir = Path(tmpdir)
            common = kernel_dir / "common"
            common.mkdir(parents=True)
            (common / "BUILD.bazel").write_text(
                "kernel_build(\n"
                '    name = "kernel_aarch64",\n'
                '    protected_module_names_list = "unexpected",\n'
                ")\n"
            )

            with self.assertRaises(RuntimeError):
                remove_protected_exports(kernel_dir)


if __name__ == "__main__":
    unittest.main()
