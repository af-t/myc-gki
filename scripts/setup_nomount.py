import argparse
import os
import subprocess
import sys
from pathlib import Path

NOMOUNT_REPO = "https://github.com/maxsteeel/nomount.git"
NOMOUNT_BRANCH = "dev"
NOMOUNT_DIR = "NoMount"


def _git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo_dir), *args], capture_output=True, text=True)


def set_config(defconfig_path: Path, key: str, value: str) -> None:
    lines = defconfig_path.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.strip() == f"# {key} is not set":
            lines[i] = f"{key}={value}\n"
            break
    else:
        lines.append(f"{key}={value}\n")
    defconfig_path.write_text("".join(lines))


def wire_nomount(kernel_dir: Path, source_dir: Path) -> None:
    fs_dir = kernel_dir / "common" / "fs"
    if not fs_dir.is_dir():
        fs_dir = kernel_dir / "fs"
    if not fs_dir.is_dir():
        raise FileNotFoundError(f"fs/ directory not found under {kernel_dir}")

    link = fs_dir / "nomount"
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        raise RuntimeError(f"refusing to replace non-symlink {link}")
    link.symlink_to(os.path.relpath(source_dir, fs_dir))

    makefile = fs_dir / "Makefile"
    make_content = makefile.read_text()
    if "CONFIG_NOMOUNT" not in make_content:
        makefile.write_text(make_content.rstrip("\n") + "\n\nobj-$(CONFIG_NOMOUNT) += nomount/\n")

    kconfig = fs_dir / "Kconfig"
    kconfig_content = kconfig.read_text()
    if 'source "fs/nomount/Kconfig"' not in kconfig_content:
        lines = kconfig_content.splitlines(keepends=True)
        last_endmenu = next(
            (i for i in range(len(lines) - 1, -1, -1) if lines[i].strip() == "endmenu"),
            None,
        )
        if last_endmenu is None:
            raise RuntimeError(f"no endmenu found in {kconfig}")
        lines.insert(last_endmenu, 'source "fs/nomount/Kconfig"\n')
        kconfig.write_text("".join(lines))

    defconfig = kernel_dir / "common" / "arch" / "arm64" / "configs" / "gki_defconfig"
    if not defconfig.is_file():
        raise FileNotFoundError(f"defconfig not found: {defconfig}")
    set_config(defconfig, "CONFIG_NOMOUNT", "y")


def _resolve_commit(repo_dir: Path) -> str | None:
    remote = _git(repo_dir, "remote", "get-url", "origin")
    if remote.returncode == 0:
        res = _git(repo_dir, "ls-remote", "origin", f"refs/heads/{NOMOUNT_BRANCH}")
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.split()[0]
    res = _git(repo_dir, "rev-parse", "HEAD")
    return res.stdout.strip() if res.returncode == 0 else None


def _checkout_commit(repo_dir: Path, commit: str) -> None:
    current = _git(repo_dir, "rev-parse", "HEAD")
    if current.returncode == 0 and current.stdout.strip() == commit:
        return
    subprocess.run(["git", "-C", str(repo_dir), "fetch", "--depth=1", "origin", commit], check=True)
    subprocess.run(["git", "-C", str(repo_dir), "checkout", "--detach", commit], check=True)


def setup_nomount(kernel_dir: Path, commit: str | None = None) -> str:
    repo_dir = kernel_dir / NOMOUNT_DIR
    if not (repo_dir / ".git").is_dir():
        subprocess.run(["git", "clone", "--no-checkout", NOMOUNT_REPO, str(repo_dir)], check=True)

    resolved = commit or _resolve_commit(repo_dir)
    if not resolved or len(resolved) != 40:
        raise ValueError(f"failed to resolve {NOMOUNT_REPO}@{NOMOUNT_BRANCH} (got: {resolved})")

    _checkout_commit(repo_dir, resolved)
    actual = _git(repo_dir, "rev-parse", "HEAD").stdout.strip()
    if actual != resolved:
        raise RuntimeError(f"NoMount commit mismatch: expected {resolved}, got {actual}")

    source_dir = repo_dir / "kernel" / "src"
    if not (source_dir / "Kconfig").is_file():
        raise RuntimeError(f"{NOMOUNT_DIR}@{resolved} has no kernel source at {source_dir}")

    wire_nomount(kernel_dir, source_dir)
    print(f"nomount_branch={NOMOUNT_BRANCH} nomount_commit={resolved}")

    github_env = os.environ.get("GITHUB_ENV")
    if github_env and Path(github_env).is_file():
        with open(github_env, "a") as env_file:
            env_file.write(f"NOMOUNT_COMMIT={resolved}\n")

    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description="Integrate NoMount VFS redirection framework.")
    parser.add_argument("--kernel-dir", type=Path, default=Path("kernel"), help="Path to kernel root (default: kernel)")
    parser.add_argument("--commit", type=str, default=None, help="Explicit NoMount commit SHA")
    args = parser.parse_args()

    try:
        setup_nomount(args.kernel_dir, args.commit)
        print("NoMount integrated")
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
