import tempfile
import unittest
from pathlib import Path

from scripts.apply_kcflags import apply_kcflags

BUILD_CONTENT = """\
common_kernel(
    name = "kernel_aarch64",
    kcflags = COMMON_KCFLAGS,
    arch = "arm64",
)

common_kernel(
    name = "kernel_aarch64_16k",
    kcflags = COMMON_KCFLAGS,
    arch = "arm64",
)
"""


class TestApplyKcflags(unittest.TestCase):
    def test_adds_flag_to_matching_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_file = Path(tmpdir) / "BUILD.bazel"
            build_file.write_text(BUILD_CONTENT)

            apply_kcflags(build_file, "kernel_aarch64", ["-O3"])

            content = build_file.read_text()
            self.assertIn(
                'name = "kernel_aarch64",\n'
                '    kcflags = COMMON_KCFLAGS + ("-O3",),\n',
                content,
            )
            self.assertIn(
                'name = "kernel_aarch64_16k",\n'
                "    kcflags = COMMON_KCFLAGS,\n",
                content,
            )

    def test_preserves_existing_flags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_file = Path(tmpdir) / "BUILD.bazel"
            build_file.write_text(
                BUILD_CONTENT.replace(
                    'name = "kernel_aarch64",\n    kcflags = COMMON_KCFLAGS,',
                    'name = "kernel_aarch64",\n    kcflags = COMMON_KCFLAGS + ("-DEXISTING",),',
                )
            )

            apply_kcflags(build_file, "kernel_aarch64", ["-O3"])

            content = build_file.read_text()
            self.assertIn(
                'kcflags = COMMON_KCFLAGS + ("-DEXISTING",) + ("-O3",),',
                content,
            )

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_file = Path(tmpdir) / "BUILD.bazel"
            build_file.write_text(BUILD_CONTENT)

            apply_kcflags(build_file, "kernel_aarch64", ["-O3"])
            apply_kcflags(build_file, "kernel_aarch64", ["-O3"])

            content = build_file.read_text()
            self.assertEqual(content.count('COMMON_KCFLAGS + ("-O3",)'), 1)

    def test_missing_target_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_file = Path(tmpdir) / "BUILD.bazel"
            build_file.write_text(BUILD_CONTENT)

            with self.assertRaises(ValueError):
                apply_kcflags(build_file, "kernel_missing", ["-O3"])


if __name__ == "__main__":
    unittest.main()
