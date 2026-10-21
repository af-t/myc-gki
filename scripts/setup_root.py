import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

LATEST_RELEASE = "latest-release"


def latest_release_tag(repo: str) -> str:
    res = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", repo],
        capture_output=True,
        text=True,
        check=True,
    )
    versions = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        name = line.split("\t", 1)[1].removeprefix("refs/tags/")
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", name)
        if match:
            versions.append((tuple(int(part) for part in match.groups()), name))
    if not versions:
        raise ValueError(f"No release tag found in {repo}")
    return max(versions)[1]


def resolve_commit(repo: str, ref: str, ref_kind: str) -> tuple[str, str]:
    if ref_kind == LATEST_RELEASE:
        ref = latest_release_tag(repo)
    if ref_kind in ("tag", LATEST_RELEASE):
        patterns = [f"refs/tags/{ref}^{{}}", f"refs/tags/{ref}"]
    else:
        patterns = [f"refs/heads/{ref}"]

    res = subprocess.run(
        ["git", "ls-remote", repo, *patterns],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"Failed to resolve {ref} in {repo}")
    peeled = [line for line in lines if line.split("\t", 1)[1].endswith("^{}")]
    commit = (peeled[0] if peeled else lines[0]).split()[0]
    return commit, ref


def get_root_spec(root_flavor: str, with_susfs: bool) -> tuple[str, str, str, str]:
    if root_flavor == "baseline":
        if with_susfs:
            raise ValueError("with_susfs requires a root flavor; baseline has no KSU source")
        return "", "", "", ""

    if root_flavor == "ksu":
        return "https://github.com/tiann/KernelSU.git", "main", "KernelSU", "branch"
    if root_flavor == "ksunext":
        if with_susfs:
            return "https://github.com/pershoot/KernelSU-Next.git", "dev-susfs", "KernelSU-Next", "branch"
        return "https://github.com/KernelSU-Next/KernelSU-Next.git", LATEST_RELEASE, "KernelSU-Next", LATEST_RELEASE
    if root_flavor == "sukisu-ultra":
        branch = "builtin" if with_susfs else "main"
        return "https://github.com/SukiSU-Ultra/SukiSU-Ultra.git", branch, "SukiSU-Ultra", "branch"
    if root_flavor in ("bakasu", "resukisu"):
        return "https://github.com/Baka-SU/BakaSU.git", "main", "BakaSU", "branch"

    raise ValueError(f"Unknown root_flavor: {root_flavor}")


def wire_kernelsu(kernel_dir: Path, source_dir: Path) -> None:
    drivers_dir = kernel_dir / "common" / "drivers"
    link_target = drivers_dir / "kernelsu"
    if link_target.exists() or link_target.is_symlink():
        raise RuntimeError("Refusing to replace existing drivers/kernelsu integration")

    rel_path = os.path.relpath(source_dir, drivers_dir)
    link_target.symlink_to(rel_path)

    makefile = drivers_dir / "Makefile"
    make_content = makefile.read_text()
    if "obj-$(CONFIG_KSU) += kernelsu/" not in make_content:
        makefile.write_text(make_content.rstrip() + "\nobj-$(CONFIG_KSU) += kernelsu/\n")

    kconfig = drivers_dir / "Kconfig"
    kc_content = kconfig.read_text()
    if kc_content.count("endmenu") != 1:
        raise RuntimeError("Unexpected endmenu count in drivers/Kconfig")
    if 'source "drivers/kernelsu/Kconfig"' not in kc_content:
        kc_content = re.sub(
            r"(\nendmenu\b)",
            r'\nsource "drivers/kernelsu/Kconfig"\1',
            kc_content,
            count=1,
        )
        kconfig.write_text(kc_content)

    defconfig = kernel_dir / "common" / "arch" / "arm64" / "configs" / "gki_defconfig"
    if defconfig.is_file():
        def_content = defconfig.read_text()
        if "CONFIG_KSU=y" not in def_content:
            defconfig.write_text(def_content.rstrip() + "\nCONFIG_KSU=y\n")


def apply_flavor_quirks(root_flavor: str, kernel_dir: Path, source_dir: Path) -> None:
    defconfig = kernel_dir / "common" / "arch" / "arm64" / "configs" / "gki_defconfig"

    if root_flavor == "ksunext":
        kbuild = source_dir / "Kbuild"
        if kbuild.is_file():
            content = kbuild.read_text()
            target = '$(error "KernelSU requires either CONFIG_KPROBES=y or CONFIG_KSU_SUSFS=y")'
            replacement = '$(warning "KernelSU requires either CONFIG_KPROBES=y or CONFIG_KSU_SUSFS=y")'
            if target in content:
                kbuild.write_text(content.replace(target, replacement))

    if root_flavor in ("bakasu", "resukisu"):
        if defconfig.is_file():
            def_content = defconfig.read_text()
            for key, value in (
                ("CONFIG_KSU_MULTI_MANAGER_SUPPORT", "n"),
                ("CONFIG_KSU_TOOLKIT_SUPPORT", "y"),
            ):
                pattern = rf"^{re.escape(key)}=.*(?:\n|$)"
                replacement = f"{key}={value}\n"
                if re.search(pattern, def_content, flags=re.MULTILINE):
                    def_content = re.sub(pattern, replacement, def_content, flags=re.MULTILINE)
                else:
                    def_content = def_content.rstrip() + f"\n{replacement}"
            defconfig.write_text(def_content)

        kbuild = source_dir / "Kbuild"
        if kbuild.is_file():
            content = kbuild.read_text()
            target = "$(error You should use $(REPO_NAME) as a git submodule instead of copying code directly)"
            replacement = "$(warning You should use $(REPO_NAME) as a git submodule instead of copying code directly)"
            if target in content:
                kbuild.write_text(content.replace(target, replacement))


def setup_root(
    kernel_dir: Path,
    root_flavor: str,
    with_susfs: bool,
    commit: str | None = None,
) -> str | None:
    if root_flavor == "baseline":
        if with_susfs:
            raise ValueError("with_susfs requires a root flavor; baseline has no KSU source")
        print("baseline selected; skipping root integration")
        return None

    repo, ref, dir_name, ref_kind = get_root_spec(root_flavor, with_susfs)
    root_dir = kernel_dir / dir_name

    for cand in ["KernelSU", "KernelSU-Next", "ReSukiSU", "SukiSU-Ultra"]:
        cand_path = kernel_dir / cand
        if cand != dir_name and cand_path.exists():
            raise RuntimeError(f"Refusing mixed root implementations: found {cand}")

    if commit:
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError(f"Expected a full commit SHA, got: {commit}")
        ref = commit
    else:
        commit, ref = resolve_commit(repo, ref, ref_kind)

    if not root_dir.exists():
        subprocess.run(["git", "clone", "--no-checkout", repo, str(root_dir)], check=True)
    subprocess.run(["git", "-C", str(root_dir), "fetch", "--depth=1", "origin", commit], check=True)
    subprocess.run(["git", "-C", str(root_dir), "checkout", "--detach", commit], check=True)

    source_dir = root_dir / "kernel"
    if not (source_dir / "Kconfig").is_file() or not (source_dir / "Makefile").is_file():
        raise RuntimeError(f"{dir_name}@{ref}@{commit} has no kernel integration")

    wire_kernelsu(kernel_dir, source_dir)
    apply_flavor_quirks(root_flavor, kernel_dir, source_dir)

    print(f"root_flavor={root_flavor} root_repo={repo} root_ref={ref} root_commit={commit}")
    github_env = os.environ.get("GITHUB_ENV")
    if github_env and Path(github_env).is_file():
        with open(github_env, "a") as env_file:
            env_file.write(f"ROOT_COMMIT={commit}\n")
            env_file.write(f"ROOT_REF={ref}\n")

    return commit


def main() -> None:
    parser = argparse.ArgumentParser(description="Integrate root implementation (KernelSU variants).")
    parser.add_argument("--kernel-dir", type=Path, default=Path("kernel"), help="Path to kernel root (default: kernel)")
    parser.add_argument("--flavor", type=str, default="baseline", help="Root flavor (baseline, ksu, ksunext, sukisu-ultra, bakasu)")
    parser.add_argument("--with-susfs", action="store_true", help="Enable SUSFS compatibility")
    parser.add_argument("--commit", type=str, default=None, help="Explicit commit SHA")
    args = parser.parse_args()

    try:
        setup_root(args.kernel_dir, args.flavor, args.with_susfs, args.commit)
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
