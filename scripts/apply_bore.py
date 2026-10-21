import argparse
import os
import subprocess
import sys
from pathlib import Path

BORE_VERSION = "7.0.0"
BORE_OPTS = [
    "CONFIG_SCHED_BORE=y",
]


def apply_bore_defconfig(defconfig_path: Path) -> None:
    lines = defconfig_path.read_text().splitlines(keepends=True)
    key_to_line = {}
    for i, line in enumerate(lines):
        if line.startswith("CONFIG_") and "=" in line:
            key = line.split("=", 1)[0]
            key_to_line[key] = i
        elif line.startswith("# CONFIG_") and line.strip().endswith(" is not set"):
            key = line.strip().split()[1]
            key_to_line[key] = i

    for opt in BORE_OPTS:
        key = opt.split("=", 1)[0]
        if key in key_to_line:
            lines[key_to_line[key]] = f"{opt}\n"
        else:
            lines.append(f"{opt}\n")

    defconfig_path.write_text("".join(lines))


def find_common_dir(kernel_dir: Path) -> Path:
    if (kernel_dir / "common" / "include" / "linux").is_dir():
        return kernel_dir / "common"
    if (kernel_dir / "include" / "linux").is_dir():
        return kernel_dir
    raise FileNotFoundError(f"Cannot find kernel common directory under {kernel_dir}")


def resolve_patch_file(patch_arg: Path | None) -> Path:
    if patch_arg is not None:
        if not patch_arg.is_file():
            raise FileNotFoundError(f"BORE patch file not found: {patch_arg}")
        return patch_arg.resolve()

    script_root = Path(__file__).resolve().parent.parent
    default_patch = script_root / "patches" / "bore-6.12.patch"
    if default_patch.is_file():
        return default_patch

    cwd_patch = Path.cwd() / "patches" / "bore-6.12.patch"
    if cwd_patch.is_file():
        return cwd_patch.resolve()

    raise FileNotFoundError(f"Default BORE patch not found at {default_patch} or {cwd_patch}")


def apply_bore(
    kernel_dir: Path,
    patch_file: Path | None = None,
    defconfig_path: Path | None = None,
) -> str:
    common_dir = find_common_dir(kernel_dir)
    patch_path = resolve_patch_file(patch_file)

    if (common_dir / ".git").is_dir():
        res = subprocess.run(
            ["git", "-C", str(common_dir), "apply", "--check", str(patch_path)],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            subprocess.run(
                ["git", "-C", str(common_dir), "apply", str(patch_path)],
                check=True,
            )
        else:
            with open(patch_path, "rb") as pf:
                subprocess.run(
                    ["patch", "--forward", "-p1", "-d", str(common_dir)],
                    stdin=pf,
                    check=True,
                )
    else:
        with open(patch_path, "rb") as pf:
            subprocess.run(
                ["patch", "--forward", "-p1", "-d", str(common_dir)],
                stdin=pf,
                check=True,
            )

    if defconfig_path is None:
        defconfig_path = common_dir / "arch" / "arm64" / "configs" / "gki_defconfig"

    if defconfig_path.is_file():
        apply_bore_defconfig(defconfig_path)

    github_env = os.environ.get("GITHUB_ENV")
    if github_env and Path(github_env).is_file():
        with open(github_env, "a") as env_file:
            env_file.write(f"BORE_VERSION={BORE_VERSION}\n")

    return BORE_VERSION


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply BORE scheduler patch and configuration.")
    parser.add_argument(
        "--kernel-dir",
        type=Path,
        default=Path("kernel"),
        help="Path to kernel directory (containing common/ or being common/)",
    )
    parser.add_argument(
        "--patch-file",
        type=Path,
        default=None,
        help="Path to bore-6.12.patch (default: patches/bore-6.12.patch)",
    )
    parser.add_argument(
        "--defconfig",
        type=Path,
        default=None,
        help="Optional explicit path to gki_defconfig",
    )
    args = parser.parse_args()

    try:
        ver = apply_bore(args.kernel_dir, args.patch_file, args.defconfig)
        print(f"BORE scheduler v{ver} applied successfully")
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
