# myc-gki - My Custom GKI

Automated CI build workflows and modular integration scripts for personal Android Generic Kernel Image (GKI) 6.12 (android16) builds.

## Credits

This project integrates, adapts, and ports patches and techniques from the following authors and open-source repositories:

- **Android Common Kernel (ACK)** - [Google / AOSP](https://android.googlesource.com/kernel/common)
  Base Android Generic Kernel Image (GKI) tree and Kleaf build infrastructure.
- **BORE (Burst-Oriented Response Enhancer) CPU Scheduler** - [Masahito Suzuki (@firelzrd)](https://github.com/firelzrd/bore-scheduler)
  Burst-oriented interactive CPU scheduler algorithmic extension adapted for KMI preservation.
- **NoMount** - [maxsteeel (@maxsteeel)](https://github.com/maxsteeel/nomount)
  In-kernel VFS path redirection framework.
- **FMRD (Fix My Root Detection)** - [af-t](https://github.com/af-t/fmrd)
  Kernel-level VFS and syscall anti-detection patch closing `/data/adb` probes, devpts root PTY ownership leaks, task visibility checks, and FUSE zero-width character lookups.
- **SUSFS (KernelSU root hiding)** - [simonpunk (@simonpunk)](https://gitlab.com/simonpunk/susfs4ksu)
  Kernel-level isolation and root evasion patches.
- **KernelSU** - [tiann (@tiann)](https://github.com/tiann/KernelSU)
  Kernel-based root solution for Android GKI devices.
- **KowSU** - [KOWX712 (@KOWX712)](https://github.com/KOWX712/KernelSU)
  KernelSU fork based on backslashxx, focused on Material theming; no SUSFS integration.
- **KernelSU-Next** - [rifsxd (@rifsxd)](https://github.com/rifsxd/KernelSU-Next)
  Active KernelSU continuation with extended patch support.
- **SukiSU-Ultra** - [The-SukiSU-Ultra-Project](https://github.com/The-SukiSU-Ultra-Project/SukiSU-Ultra)
  KernelSU-based root flavor for GKI kernels.
- **BakaSU** - [Baka-SU](https://github.com/Baka-SU/BakaSU)
  KernelSU-based root solution for Android GKI (formerly ReSukiSU).
- **Wild-style / Kernel Bypass Techniques**
  Implementation techniques for module symbol CRC mismatch bypass and removing protected symbol restrictions.

## DWYOR

This repository and its resulting kernel builds are personal experimental projects provided as-is. Flashing custom kernels involves inherent risks including bootloops, data loss, or bricked devices. Always keep a verified backup of your stock boot images (`boot`, `init_boot`, `vbmeta`) and ensure your bootloader recovery paths are accessible before flashing. Do with your own risk.
