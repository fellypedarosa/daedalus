---
tags: [linux, operating_systems, boot]
date_created: 2026-04-12
sources:
  - "[[Akitando 127 - Como Funciona o Boot de um Linux  O que tem num LiveCD]] (Clipper)"
---
# Linux Boot Process

The Linux boot process is a multi-stage orchestration that transitions control from hardware firmware to the finalized operating system environment.

## 1. Hardware Initialization (UEFI/BIOS)
Upon power-on, the motherboard's firmware (**UEFI** in modern systems, legacy **BIOS** in older ones) initializes the CPU, RAM, and essential peripherals. It then scans for a bootable device by looking for the **EFI System Partition (ESP)**, typically mounted at `/boot/efi`.

## 2. The Bootloader (GRUB)
The firmware hands off execution to the **Bootloader**, most commonly the **GRUB (Grand Unified Bootloader)**.
- **Kernel Parameters**: GRUB allows users to intercept the boot process (by holding `Shift`) and edit kernel parameters (e.g., changing the default runlevel or adding `nomodeset`).
- **Function**: GRUB's primary role is to find the Linux Kernel image on the disk and load it into memory.

## 3. Kernel and Initramfs
Once the Kernel initializes, it mounts a temporary, compressed filesystem in RAM called the **initramfs** (Initial RAM File System), which contains the **initrd** (Initial RAM Disk). 
- **Purpose**: This filesystem contains essential drivers (like filesystem drivers or network protocols) needed to mount the actual root partition (`/`) from the storage drive.

## 4. Initialization (PID 1)
After the root filesystem is mounted, the Kernel launches the first process, assigned **Process ID 1 (PID 1)**. In modern distributions, this is usually **SystemD**. SystemD then takes over, orchestrating the loading of all background services and the graphical interface.
