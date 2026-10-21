import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SUSFS_BRANCH = "gki-android16-6.12"
SUSFS_REPO = "https://gitlab.com/simonpunk/susfs4ksu.git"
SUSFS_COMMIT = "acb92d4abc922cac384a207744b2db40281a7c7f"

SUSFS_OPTS = [
    "CONFIG_KSU_SUSFS=y",
    "CONFIG_KSU_SUSFS_SUS_PATH=y",
    "CONFIG_KSU_SUSFS_SUS_MOUNT=y",
    "CONFIG_KSU_SUSFS_SUS_KSTAT=y",
    "CONFIG_KSU_SUSFS_SPOOF_UNAME=y",
    "CONFIG_KSU_SUSFS_ENABLE_LOG=y",
    "CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y",
    "CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y",
    "CONFIG_KSU_SUSFS_SUS_MAP=y",
    "CONFIG_KSU_SUSFS_OPEN_REDIRECT=y",
]


def apply_susfs_defconfig(defconfig_path: Path) -> None:
    lines = defconfig_path.read_text().splitlines(keepends=True)
    key_to_line = {}
    for i, line in enumerate(lines):
        if line.startswith("CONFIG_") and "=" in line:
            key = line.split("=", 1)[0]
            key_to_line[key] = i

    for opt in SUSFS_OPTS:
        key = opt.split("=", 1)[0]
        if key in key_to_line:
            lines[key_to_line[key]] = f"{opt}\n"
        else:
            lines.append(f"{opt}\n")

    defconfig_path.write_text("".join(lines))


def patch_task_mmu(kernel_common: Path) -> None:
    target = kernel_common / "fs" / "proc" / "task_mmu.c"
    if not target.is_file():
        return

    content = target.read_text()
    if "VMA_PAD_START(" in content and not re.search(
        r"#include <linux/pgsize_migration(_inline)?\.h>|define VMA_PAD_START",
        content,
    ):
        header = "#ifndef VMA_PAD_START\n#define VMA_PAD_START(vma) ((vma)->vm_end)\n#endif\n"
        target.write_text(header + content)


def patch_selinux_hide(kernel_common: Path) -> None:
    for target in kernel_common.glob("**/selinux_hide.c"):
        content = target.read_text()
        if "extern void security_dump_masked_av_fn" in content:
            content = content.replace("if (security_dump_masked_av_fn)", "if (&security_dump_masked_av_fn)")
            content = content.replace(
                "if (security_dump_masked_av_fn != NULL)",
                "if (&security_dump_masked_av_fn != NULL)",
            )
            content = content.replace(
                "if (context_struct_compute_av_fn)",
                "if (&context_struct_compute_av_fn)",
            )
            content = content.replace(
                "if (context_struct_compute_av_fn != NULL)",
                "if (&context_struct_compute_av_fn != NULL)",
            )
            target.write_text(content)
        elif "if (security_dump_masked_av_fn" in content:
            content = content.replace(
                "if (security_dump_masked_av_fn)",
                "if (security_dump_masked_av_fn != NULL)",
            )
            content = content.replace(
                "if (context_struct_compute_av_fn)",
                "if (context_struct_compute_av_fn != NULL)",
            )
            target.write_text(content)


def copy_tree_files(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.is_dir():
        return
    for item in src_dir.iterdir():
        target = dst_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def apply_susfs(
    workspace_root: Path,
    root_flavor: str,
    susfs_dir: Path | None = None,
) -> str:
    if susfs_dir is None:
        susfs_dir = workspace_root / "susfs4ksu"
        if not susfs_dir.exists():
            subprocess.run(
                ["git", "clone", "--no-checkout", "-b", SUSFS_BRANCH, SUSFS_REPO, str(susfs_dir)],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(susfs_dir), "checkout", "--detach", SUSFS_COMMIT],
                check=True,
            )

    res = subprocess.run(["git", "-C", str(susfs_dir), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    sha = res.stdout.strip()
    print(f"susfs_branch={SUSFS_BRANCH} susfs_commit={sha}")

    github_env = os.environ.get("GITHUB_ENV")
    if github_env and Path(github_env).is_file():
        with open(github_env, "a") as env_file:
            env_file.write(f"SUSFS_COMMIT={sha}\n")

    if root_flavor == "ksu":
        patch_file = susfs_dir / "kernel_patches" / "KernelSU" / "10_enable_susfs_for_ksu.patch"
        if not patch_file.is_file():
            raise FileNotFoundError(f"Missing {patch_file}")
        ksu_dir = workspace_root / "kernel" / "KernelSU"
        with open(patch_file, "rb") as pf:
            subprocess.run(["patch", "--forward", "-p1", "-d", str(ksu_dir)], stdin=pf, check=True)

    defconfig = workspace_root / "kernel" / "common" / "arch" / "arm64" / "configs" / "gki_defconfig"
    if defconfig.is_file():
        apply_susfs_defconfig(defconfig)

    kernel_common = workspace_root / "kernel" / "common"
    copy_tree_files(susfs_dir / "kernel_patches" / "fs", kernel_common / "fs")
    copy_tree_files(susfs_dir / "kernel_patches" / "include" / "linux", kernel_common / "include" / "linux")

    patch_50 = susfs_dir / "kernel_patches" / "50_add_susfs_in_gki-android16-6.12.patch"
    dst_patch = kernel_common / "50_add_susfs_in_gki-android16-6.12.patch"
    shutil.copy2(patch_50, dst_patch)
    with open(dst_patch, "rb") as pf:
        subprocess.run(["patch", "--forward", "-p1", "-d", str(kernel_common)], stdin=pf, check=True)

    patch_task_mmu(kernel_common)
    patch_selinux_hide(kernel_common)
    return sha


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply SUSFS patches and configuration.")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Workspace root (default: current dir)")
    parser.add_argument("--flavor", type=str, default="baseline", help="Root flavor (ksu, ksunext, sukisu-ultra, bakasu)")
    parser.add_argument("--susfs-dir", type=Path, default=None, help="Existing susfs4ksu repo directory")
    args = parser.parse_args()

    try:
        apply_susfs(args.workspace, args.flavor, args.susfs_dir)
        print("SUSFS applied")
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
