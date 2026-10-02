# myc-gki - Baseline GKI 6.12.38 (android16)

A personal kernel project built **only in CI** through a manual workflow trigger.
Pinned: `6.12.38` with SPL `2025-09`, cloned directly from `kernel/common` tag `android16-6.12-2025-09_r38`.

> CI cannot use a local kernel tree directly. It shallow-clones the pinned `kernel/common` tag above, verifies the pinned SHA, then applies the selected CI patches. Local-only changes must be added to this repository as patches or config before CI can reproduce them.

## Build (CI only; no local build)

1. Open **Actions** -> **Build baseline**.
2. Select **Run workflow** -> choose `spl`: `All` or `2025-09` (`2025-09` is the default).
3. Leave `brand_name` empty to keep the stock GKI version string.
4. `allow_version_mismatch` is on by default so modules ported from Wild can load despite symbol version differences.
5. Download the result from **Artifacts**: `Image-6.12.38-android16-<spl>` and `BuildInfo`.

## Repository contents

- `.github/workflows/build.yml` - the only workflow; it is triggered manually.
- `.github/config/android16-6.12.json` - pinned common remote/tag/SHA, sublevel, and dates; source of truth for the matrix.
- `configs/baseline.fragment` - placeholder for your own defconfig tweaks (ZRAM, BBG, etc.).
- Build = stock AOSP plus the minimal glibc `resolve_btfids` compiler fix, without KSU or SUSFS.
- Optional branding preserves the KMI generation when supplied; an empty brand keeps the stock version.
- Optional version-mismatch bypass uses the Wild-style `bad_version` patch. It can allow a mismatched external module to load, but it does not add a missing driver, firmware, or device binding.

## Planned tweaks (not enabled)

Add lines to `configs/baseline.fragment`, for example, GKID-style:

```ini
CONFIG_SWAP=y
CONFIG_ZRAM_DEF_COMP_LZ4=y
CONFIG_ZRAM_WRITEBACK=y
CONFIG_ZRAM_MEMORY_TRACKING=y
```
