# myc-gki - Baseline GKI 6.12.38 (android16)

A personal kernel project built **only in CI** through a manual workflow trigger.
Pinned: `6.12.38` with SPL `2025-09` and `2025-10`.

> AOSP branch status (checked 2026-09-13):
> - `common-android16-6.12-2025-09` is available.
> - `common-android16-6.12-2025-10` has not been published yet. The workflow will fail with a clear message if selected and will work automatically once Google publishes the branch. No workflow changes are required.

## Build (CI only; no local build)

1. Open **Actions** -> **Build baseline**.
2. Select **Run workflow** -> choose `spl`: `All`, `2025-09`, or `2025-10`.
3. Download the result from **Artifacts**: `Image-6.12.38-android16-<spl>` and `BuildInfo`.

## Repository contents

- `.github/workflows/build.yml` - the only workflow; it is triggered manually.
- `.github/config/android16-6.12.json` - pinned sublevel and dates; source of truth for the matrix.
- `configs/baseline.fragment` - placeholder for your own defconfig tweaks (ZRAM, BBG, etc.).
- Build = stock AOSP plus the minimal glibc `resolve_btfids` compiler fix, without KSU or SUSFS.

## Planned tweaks (not enabled)

Add lines to `configs/baseline.fragment`, for example, GKID-style:

```ini
CONFIG_SWAP=y
CONFIG_ZRAM_DEF_COMP_LZ4=y
CONFIG_ZRAM_WRITEBACK=y
CONFIG_ZRAM_MEMORY_TRACKING=y
```
