import argparse
import re
import sys
from pathlib import Path

FRAGMENT_PATTERN = re.compile(r"^CONFIG_[A-Za-z0-9_]+=.+$")


def validate_fragment(fragment_path: Path) -> list[str]:
    if not fragment_path.is_file():
        raise FileNotFoundError(f"Fragment file not found: {fragment_path}")

    opts = []
    bad_lines = []
    for line in fragment_path.read_text().splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if FRAGMENT_PATTERN.match(trimmed):
            opts.append(trimmed)
        else:
            bad_lines.append(line)

    if bad_lines:
        raise ValueError(f"Malformed fragment lines in {fragment_path}:\n" + "\n".join(bad_lines))

    return opts


def apply_fragment(fragment_path: Path, defconfig_path: Path) -> list[str]:
    if not defconfig_path.is_file():
        raise FileNotFoundError(f"defconfig not found: {defconfig_path}")

    opts = validate_fragment(fragment_path)
    if not opts:
        return []

    lines = defconfig_path.read_text().splitlines(keepends=True)
    key_to_line = {}
    for i, line in enumerate(lines):
        if line.startswith("CONFIG_") and "=" in line:
            key = line.split("=", 1)[0]
            key_to_line[key] = i

    for opt in opts:
        key = opt.split("=", 1)[0]
        if key in key_to_line:
            lines[key_to_line[key]] = f"{opt}\n"
        else:
            lines.append(f"{opt}\n")

    defconfig_path.write_text("".join(lines))
    return opts


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and merge a Kconfig fragment into defconfig.")
    parser.add_argument(
        "--fragment",
        type=Path,
        default=Path("configs/baseline.fragment"),
        help="Path to fragment file (default: configs/baseline.fragment)",
    )
    parser.add_argument(
        "--defconfig",
        type=Path,
        default=Path("kernel/common/arch/arm64/configs/gki_defconfig"),
        help="Path to defconfig file (default: kernel/common/arch/arm64/configs/gki_defconfig)",
    )
    args = parser.parse_args()

    try:
        applied = apply_fragment(args.fragment, args.defconfig)
        if applied:
            print("fragment applied:\n" + "\n".join(applied))
        else:
            print("fragment empty; nothing to apply")
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
