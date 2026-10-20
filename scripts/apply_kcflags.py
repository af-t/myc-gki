import argparse
import json
import sys
from pathlib import Path


def _target_bounds(lines: list[str], target: str) -> tuple[int, int]:
    target_idx = None
    for i, line in enumerate(lines):
        if f'name = "{target}",' in line:
            target_idx = i
            break
    if target_idx is None:
        raise ValueError(f'target "{target}" not found')

    end_idx = len(lines)
    for i in range(target_idx + 1, len(lines)):
        if "common_kernel(" in lines[i]:
            end_idx = i
            break
    return target_idx, end_idx


def apply_kcflags(build_file: Path, target: str, flags: list[str]) -> Path:
    if not flags:
        raise ValueError("at least one flag is required")

    lines = build_file.read_text().splitlines(keepends=True)
    start, end = _target_bounds(lines, target)

    kcflags_idx = None
    for i in range(start + 1, end):
        if lines[i].lstrip().startswith("kcflags ="):
            kcflags_idx = i
            break
    if kcflags_idx is None:
        raise ValueError(f"'kcflags =' not found for target \"{target}\" in {build_file}")

    line = lines[kcflags_idx]
    if "COMMON_KCFLAGS" not in line:
        raise ValueError(f"unexpected kcflags value for target \"{target}\" in {build_file}")
    expression = line.split("=", 1)[1].strip().rstrip(",")
    if all(json.dumps(flag) in expression for flag in flags):
        return build_file

    indent = line[: len(line) - len(line.lstrip())]
    rendered = ", ".join(json.dumps(flag) for flag in flags)
    lines[kcflags_idx] = f"{indent}kcflags = {expression} + ({rendered},),\n"
    build_file.write_text("".join(lines))
    return build_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Append flags to a kernel_build kcflags list.")
    parser.add_argument(
        "--build-file",
        type=Path,
        default=Path("common/BUILD.bazel"),
        help="Path to BUILD.bazel (default: common/BUILD.bazel)",
    )
    parser.add_argument(
        "--target",
        default="kernel_aarch64",
        help="kernel_build target name (default: kernel_aarch64)",
    )
    parser.add_argument(
        "--flag",
        action="append",
        required=True,
        help="Flag to append; use --flag=-O3 when the flag starts with a dash",
    )
    args = parser.parse_args()

    try:
        patched_file = apply_kcflags(args.build_file, args.target, args.flag)
        print(f"Applied kcflags to {patched_file}")
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
