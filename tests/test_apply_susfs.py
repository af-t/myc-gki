import tempfile
import unittest
from pathlib import Path

from scripts.apply_susfs import (
    apply_susfs_defconfig,
    patch_selinux_hide,
    patch_task_mmu,
)


class TestApplySusfs(unittest.TestCase):
    def test_apply_susfs_defconfig(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("CONFIG_EXISTING=y\n")
            f.flush()
            defconfig = Path(f.name)
            apply_susfs_defconfig(defconfig)
            content = defconfig.read_text().splitlines()
            self.assertIn("CONFIG_KSU_SUSFS=y", content)
            self.assertIn("CONFIG_KSU_SUSFS_OPEN_REDIRECT=y", content)

    def test_patch_task_mmu(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            proc = base / "fs" / "proc"
            proc.mkdir(parents=True)
            target = proc / "task_mmu.c"
            target.write_text("static void foo() { VMA_PAD_START(vma); }\n")
            patch_task_mmu(base)
            content = target.read_text()
            self.assertIn("#define VMA_PAD_START(vma)", content)

    def test_patch_selinux_hide(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "security" / "selinux_hide.c"
            target.parent.mkdir(parents=True)
            target.write_text("extern void security_dump_masked_av_fn();\nif (security_dump_masked_av_fn) {}\n")
            patch_selinux_hide(base)
            content = target.read_text()
            self.assertIn("&security_dump_masked_av_fn", content)


if __name__ == "__main__":
    unittest.main()
