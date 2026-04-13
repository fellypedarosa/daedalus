---
tags: [infrastructure, os, windows, unix, licensing]
date_created: 2026-04-12
sources:
  - "[[Akitando 60 - Entendendo WSL 2 | E uma curta história sobre Windows NT]] (Clipper)"
  - "[[Akitando 42 - Apple, GPL e Compiladores]] (Clipper)"
---
# Operating Systems History and Architecture

Understanding the shared lineage and divergent philosophies of modern Operating Systems (OS) is critical for system administration and software engineering.

## Windows NT: The Corporate Giant

Developed in the early 1990s by **Dave Cutler** (who led the VMS project at DEC), Windows NT (New Technology) was designed to be portable and robust.
- **WNT Logic**: According to Cutler, "WNT" is a "VMS+1" letter-shift (V->W, M->N, S->T), similar to IBM being a shift of HAL.
- **Microkernel vs. Hybrid**: NT started as a modular microkernel design. However, to resolve performance overhead from constant context-switching (IPC between Ring-3 and Ring-0), many components (Graphics, Drivers) were moved into the kernel space, resulting in a **Hybrid Kernel**.
- **Object Manager**: Internally, everything in NT (files, processes, threads) is managed as a logical "Object."
- **HAL (Hardware Abstraction Layer)**: A low-level layer that hides hardware differences (CPU types) from the rest of the OS, enabling portability from x86 to MIPS, Alpha, and now ARM.

## The Unix Lineage

### BSD vs. Linux
- **BSD (Berkeley Software Distribution)**: A direct descendant of the original AT&T Unix. Used as the foundation for **macOS (Darwin)** and **nextStep**.
- **Linux**: A "Unix-like" kernel developed from scratch by Linus Torvalds. It is not "Unix" by license, only by behavior (POSIX compliance).

### Licensing Politics: GPL v2 vs. v3
The choice of license has shaped entire ecosystems:
- **GPL v2**: Used by the Linux Kernel. Allows commercial use but requires modifications to be shared.
- **GPL v3 (Anti-Tivoization)**: Introduced clauses to prevent "Tivoization" (using GPL software in hardware that is locked via digital signatures to prevent user modification).
- **The Fallout**: Companies like **Apple** and **Google** (for certain components) avoid GPL v3 software to maintain control over hardware-software integration. This led Apple to shift from the **GCC** compiler to **LLVM/Clang** and keep older versions of tools like **Bash** (3.2) to avoid v3 compliance.

## Subsystem Personalities

Universal OSs often support "Personalities" to run software from other systems:
- **POSIX Subsystem**: An early NT feature to support Unix source code (for government contracts).
- **WoW64 (Windows 32 on Windows 64)**: Allows 32-bit applications to run on 64-bit Windows through a compatibility layer.
- **Wine (Wine Is Not an Emulator)**: A compatibility layer that translates Windows API calls to Linux syscalls in real-time. It is "black-box" engineering, reimplementing Windows DLLs from scratch.
- **Proton**: A Steam-specific distribution of Wine optimized for high-performance gaming on Linux.
