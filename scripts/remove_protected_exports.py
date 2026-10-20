import argparse
import re
import shutil
import sys
from pathlib import Path


def remove_protected_exports(kernel_dir: Path) -> None:
    common_dir = kernel_dir / "common"
    if not common_dir.is_dir():
        common_dir = kernel_dir

    android_dir = common_dir / "android"
    if android_dir.is_dir():
        for path in android_dir.glob("abi_gki_protected_exports_*"):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        remaining = list(android_dir.glob("abi_gki_protected_exports_*"))
        if remaining:
            raise RuntimeError(f"Failed to remove exports: {remaining}")

    build_bazel = common_dir / "BUILD.bazel"
    if build_bazel.is_file():
        content = build_bazel.read_text()
        content = re.sub(
            r'^[ \t]*"protected_exports_list"[ \t]*:[ \t]*"android/abi_gki_protected_exports_aarch64",?[ \t]*\n?',
            "",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r'^[ \t]*protected_module_names_list[ \t]*=[ \t]*":gki_(?:aarch64|x86_64)_protected_module_names",?[ \t]*\n?',
            "",
            content,
            flags=re.MULTILINE,
        )
        build_bazel.write_text(content)

    modules_bzl = common_dir / "modules.bzl"
    if modules_bzl.is_file():
        content = modules_bzl.read_text()
        content = re.sub(
            r"protected_modules\s*=\s*\[[^\]]*\]",
            "protected_modules = []",
            content,
        )
        modules_bzl.write_text(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove GKI protected exports to allow vendor modules.")
    parser.add_argument(
        "--kernel-dir",
        type=Path,
        default=Path("kernel"),
        help="Path to kernel root directory (default: kernel)",
    )
    args = parser.parse_args()

    try:
        remove_protected_exports(args.kernel_dir)
        print("Protected exports removed")
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
