import tempfile
import unittest
from pathlib import Path

from scripts.setup_root import (
    apply_flavor_quirks,
    get_root_spec,
    wire_kernelsu,
)


class TestSetupRoot(unittest.TestCase):
    def test_get_root_spec(self):
        repo, branch, dir_name = get_root_spec("ksu", False)
        self.assertEqual(dir_name, "KernelSU")
        self.assertEqual(branch, "main")

        repo, branch, dir_name = get_root_spec("ksunext", True)
        self.assertEqual(dir_name, "KernelSU-Next")
        self.assertEqual(branch, "dev-susfs")

        repo, branch, dir_name = get_root_spec("sukisu-ultra", True)
        self.assertEqual(branch, "builtin")

        with self.assertRaises(ValueError):
            get_root_spec("baseline", True)

        with self.assertRaises(ValueError):
            get_root_spec("invalid", False)

    def test_wire_kernelsu(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            drivers = base / "common" / "drivers"
            drivers.mkdir(parents=True)
            arch_configs = base / "common" / "arch" / "arm64" / "configs"
            arch_configs.mkdir(parents=True)

            (drivers / "Makefile").write_text("obj-y += existing/\n")
            (drivers / "Kconfig").write_text("menu \"Drivers\"\nendmenu\n")
            (arch_configs / "gki_defconfig").write_text("CONFIG_FOO=y\n")

            dummy_src = base / "KernelSU" / "kernel"
            dummy_src.mkdir(parents=True)
            (dummy_src / "Kconfig").write_text("# dummy")
            (dummy_src / "Makefile").write_text("# dummy")

            wire_kernelsu(base, dummy_src)

            self.assertTrue((drivers / "kernelsu").is_symlink())
            self.assertIn("obj-$(CONFIG_KSU) += kernelsu/", (drivers / "Makefile").read_text())
            self.assertIn('source "drivers/kernelsu/Kconfig"', (drivers / "Kconfig").read_text())
            self.assertIn("CONFIG_KSU=y", (arch_configs / "gki_defconfig").read_text())

    def test_apply_flavor_quirks_resukisu_overrides_conflicts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            arch_configs = base / "common" / "arch" / "arm64" / "configs"
            arch_configs.mkdir(parents=True)
            defconfig = arch_configs / "gki_defconfig"
            defconfig.write_text(
                "CONFIG_KSU_MULTI_MANAGER_SUPPORT=y\n"
                "CONFIG_KSU_TOOLKIT_SUPPORT=n\n"
            )

            dummy_src = base / "ReSukiSU" / "kernel"
            dummy_src.mkdir(parents=True)
            (dummy_src / "Kbuild").write_text("# dummy")

            apply_flavor_quirks("resukisu", base, dummy_src)
            apply_flavor_quirks("resukisu", base, dummy_src)

            content = defconfig.read_text()
            self.assertIn("CONFIG_KSU_MULTI_MANAGER_SUPPORT=n", content)
            self.assertIn("CONFIG_KSU_TOOLKIT_SUPPORT=y", content)
            self.assertNotIn("CONFIG_KSU_MULTI_MANAGER_SUPPORT=y", content)
            self.assertNotIn("CONFIG_KSU_TOOLKIT_SUPPORT=n", content)

    def test_apply_flavor_quirks_ksunext(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            dummy_src = base / "KernelSU-Next" / "kernel"
            dummy_src.mkdir(parents=True)
            kbuild = dummy_src / "Kbuild"
            kbuild.write_text('$(error "KernelSU requires either CONFIG_KPROBES=y or CONFIG_KSU_SUSFS=y")')

            apply_flavor_quirks("ksunext", base, dummy_src)
            self.assertIn("$(warning", kbuild.read_text())


if __name__ == "__main__":
    unittest.main()
