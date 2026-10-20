import argparse
import re
import sys

SUBLEVEL_PATTERN = re.compile(r"^[0-9]+$")


def validate_sublevel(value: str) -> int:
    cleaned = value.strip()
    if not SUBLEVEL_PATTERN.fullmatch(cleaned):
        raise ValueError(f"sublevel must be a non-negative integer, got: {value!r}")
    return int(cleaned)


def build_version(kernel_part: str, sublevel: int, android_part: str, kmi: str, brand: str = "") -> str:
    version = f"{kernel_part}.{sublevel}-{android_part}-{kmi}"
    if brand:
        version += f"-{brand}"
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description="Format a cosmetic kernel sublevel override.")
    parser.add_argument("--kernel-part", required=True)
    parser.add_argument("--sublevel", required=True)
    parser.add_argument("--android-part", required=True)
    parser.add_argument("--kmi", required=True)
    parser.add_argument("--brand", default="")
    args = parser.parse_args()

    try:
        sublevel = validate_sublevel(args.sublevel)
        print(build_version(args.kernel_part, sublevel, args.android_part, args.kmi, args.brand))
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
