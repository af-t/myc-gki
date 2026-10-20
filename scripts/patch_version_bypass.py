import argparse
import sys
from pathlib import Path


def patch_version_bypass(kernel_dir: Path) -> Path:
    target = kernel_dir / "kernel" / "module" / "version.c"
    if not target.is_file():
        target = kernel_dir / "kernel" / "module.c"
    if not target.is_file():
        raise FileNotFoundError(f"Neither version.c nor module.c found in {kernel_dir}")

    lines = target.read_text().splitlines(keepends=True)
    found_bad_version = False
    patched = False

    for i, line in enumerate(lines):
        if "bad_version:" in line:
            found_bad_version = True
            for j in range(i + 1, min(i + 10, len(lines))):
                if "return 0;" in lines[j]:
                    lines[j] = lines[j].replace("return 0;", "return 1;")
                    patched = True
                    break
            break

    if not found_bad_version:
        raise ValueError(f"'bad_version:' label not found in {target}")
    if not patched:
        raise ValueError(f"Could not patch 'return 0;' after 'bad_version:' in {target}")

    target.write_text("".join(lines))
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Wild-style module version mismatch bypass.")
    parser.add_argument(
        "--kernel-dir",
        type=Path,
        default=Path("kernel/common"),
        help="Path to kernel common tree (default: kernel/common)",
    )
    args = parser.parse_args()

    try:
        patched_file = patch_version_bypass(args.kernel_dir)
        print(f"Version-mismatch bypass applied to {patched_file}")
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
