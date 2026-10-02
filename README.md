# myc-gki - Personal GKI 6.12.38 (android16)

A personal kernel project built **only in CI** through a manual workflow trigger.
Pinned: `6.12.38` with SPL `2025-09`; CI syncs the kernel manifest, then pins `kernel/common` to tag `android16-6.12-2025-09_r38` at the verified SHA.

> CI cannot use a local kernel tree directly. It syncs (or reuses a cached) kernel tree, verifies the pinned SHA, then applies the selected patches. Local-only changes must be added to this repository as config before CI can reproduce them.

## Build (CI only; no local build)

1. Open **Actions** -> **Build kernel**.
2. Select **Run workflow** -> choose `spl` (`2025-09` is the default).
3. Leave `brand_name` empty to keep the stock GKI version string.
4. Defaults load vendor modules (`allow_version_mismatch`, `remove_protected_exports` on) and reuse cached source (`use_source_cache` on).
5. Optional root: pick `root_flavor` (`ksu`, `ksunext`, `sukisu-ultra`, `resukisu`) and/or tick `with_susfs`. SUSFS needs a root flavor; the matching manager app is installed manually.
6. Download the result from **Artifacts**: `Image-6.12.38-android16-<spl>` and `BuildInfo` (records the exact inputs and commits used).

## Repository contents

- `.github/workflows/build.yml` - the only workflow; triggered manually.
- `.github/config/android16-6.12.json` - pinned common remote/tag/SHA, sublevel, and dates; source of truth for the matrix.
- `configs/baseline.fragment` - personal defconfig tweaks merged into `gki_defconfig` at build time (currently namespaces + tmpfs xattr/ACL).
- Default build = stock AOSP plus: glibc `resolve_btfids` compiler fix, version-mismatch bypass, protected-exports removal, and the fragment above. No root unless `root_flavor` is set.
- Optional branding preserves the KMI generation when supplied; an empty brand keeps the stock version.
- Optional version-mismatch bypass uses the Wild-style `bad_version` patch. It can allow a mismatched external module to load, but it does not add a missing driver, firmware, or device binding.
