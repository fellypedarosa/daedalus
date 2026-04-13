---
tags: [linux, operating_systems, philosophy]
date_created: 2026-04-12
sources:
  - "[[Akitando 128 - Entendendo Pacotes com Slackware]] (Clipper)"
  - "[[Akitando 129 - Apanhando do Gentoo]] (Clipper)"
---
# Linux Distribution Philosophies

The diversity of Linux distributions arises from competing philosophies regarding ease of use, stability, and hardware optimization.

## The KISS Principle (Slackware)
Slackware, the oldest active distribution, follows the **KISS (Keep It Simple, Stupid)** philosophy.
- **Minimal Automation**: It avoids complex dependency solvers. The system assumes that if a library is needed, the administrator should have installed it.
- **"Install Everything" Paradigm**: To avoid "Dependency Hell," Slackware's traditional installation strategy is to simply install every package provided, ensuring all base libraries are present.
- **Transparency**: Tools like `installpkg` are simple shell scripts, allowing the administrator to see exactamente how the system is being modified.

## The Theory of Tuning (Gentoo)
Gentoo focuses on extreme hardware optimization through source-based compilation.
- **Custom Kernels**: Unlike "fat" generic kernels in Ubuntu/Fedora, Gentoo encourages stripping unneeded drivers (e.g., PCMCIA, legacy SCSI) to reduce memory footprint.
- **USE Flags**: A mechanism to define which features should be compiled into a software (e.g., compiling GNOME without `systemd` support by using `elogind`).
- **The Stockholm Syndrome Effect**: Akita notes that the high "cost" of entry (hours of compilation and configuration) creates a psychological attachment (Sunk Cost Fallacy) where users become fiercely loyal to the distro because of the effort invested.

## Categorization: Binary vs. Source
| Feature | Binary (Ubuntu/Slackware) | Source (Gentoo) |
| :--- | :--- | :--- |
| **Convenience** | High (Pre-compiled) | Low (Compiling takes hours) |
| **Optimization** | Generic (Fits all) | Specific (Optimized for $YOUR\_CPU$) |
| **Visibility** | Opaque (Black box bin) | Transparent (Code-level awareness) |
| **RAM usage** | Higher (Loaded drivers) | Minimal (Tailored kernel) |
