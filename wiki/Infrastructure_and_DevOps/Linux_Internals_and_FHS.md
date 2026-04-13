---
tags: [infrastructure, linux, kernel, sysadmin]
date_created: 2026-04-12
sources:
  - "[[Akitando 54 - O Guia DEFINITIVO de UBUNTU para Devs Iniciantes.md]] (Clipper)"
---
# Linux Internals and FHS

The Linux Filesystem Hierarchy Standard (FHS) defines the structure and contents of directories in Unix-like operating systems.

## The Root Hierarchy (`/`)

| Directory | Purpose |
| :--- | :--- |
| `/bin` | Essential command binaries (e.g., `bash`, `ls`, `cp`). |
| `/sbin` | System binaries for administration (e.g., `iptables`, `fdisk`, `reboot`). |
| `/etc` | System-wide **Configuration files**. |
| `/usr` | "Unix System Resources." Contains the majority of user utilities and applications. |
| `/var` | "Variable" data (logs, spool files, temporary databases). |
| `/boot` | Static files of the boot loader (Kernel images like `vmlinuz`, `initrd.img`). |
| `/root` | Home directory for the `root` user (Administrator). |
| `/home` | Base directory for user home directories. |
| `/opt` | Optional/Add-on software packages. |
| `/tmp` | Temporary files (often cleared on reboot). |

## Pseudo-Filesystems (Kernel Interfaces)

Linux treats "everything as a file." These directories do not exist on disk but are interfaces to the kernel:

### `/proc` (Process Information)
- Exposes internal kernel data structures.
- **Example**: `/proc/[pid]/status` contains information about a specific running process.
- **Tools**: `ps`, `top`, and `kill` read from this directory.

### `/sys` (System/Hardware)
- Provides information about hardware, drivers, and kernel features.
- Used to manage power settings, CPU frequency, and device parameters.

### `/dev` (Devices)
- Represents hardware devices as files.
- **Examples**: `/dev/sda` (Hard drive), `/dev/null` (The black hole for output), `/dev/random`.

## Filesystem Abstraction (VFS)

The Linux Kernel uses a **Virtual File System (VFS)** layer to abstract the details of specific filesystems ([[Storage_and_Filesystems|ext4, XFS]], NFS) from the applications.

### Key Data Structures (`fs.h`)
- **Superblock**: The root of the filesystem. Defines the FS type, size, and status.
- **Inode (Index Node)**: Represents a file or directory object.
    - Contains metadata: `uid`, `gid`, `timestamps`, `permissions`.
    - Does **not** contain the filename (stored in dentry).
    - Can be inspected via `stat` command.
- **Dentry (Directory Entry)**: Maps filenames to Inodes. Maintains the hierarchy/tree structure.
- **File Object**: Represents an open file in a specific process's context.

---

## The Linux Boot Sequence

The boot process is a transition from hardware-specific code to the generic OS kernel.

### UEFI and GPT
Modern systems use **UEFI (Unified Extensible Firmware Interface)** and **GPT (GUID Partition Table)**. See [[Storage_and_Filesystems#Boot Architecture|Boot Architecture]] for MBR vs GPT.
- **ESP (EFI System Partition)**: A small FAT32 partition containing `.efi` binaries (bootloaders).
- **Secure Boot**: A protocol where the UEFI firmware only loads binaries signed by a trusted key (often Microsoft's), preventing rootkits from loading before the OS. See [[Digital_Signatures_and_GPG|Digital Signatures]] and [[Operating_System_Security|OS Security]].

### Kernel and Initramfs
1.  **Bootloader**: (GRUB, systemd-boot) loads the **Vmlinuz** (compressed kernel) and **initramfs** into memory.
2.  **Initramfs**: A temporary root filesystem in RAM. It contains the essential drivers (LVM, LUKS, RAID, NVMe) needed to mount the *real* root partition. 
3.  **The Switch**: Once the real `/` is mounted, the kernel executes the `init` process (PID 1) and discards the initramfs.

### Init Systems (systemd vs. SysV)
- **SysV Init**: Procedural. Executes scripts in `/etc/init.d/` sequentially based on runlevels (1-6). Slow and inflexible.
- **systemd**: Parallel and declarative. Uses **Units** (.service, .mount, .target). See [[Systemd_and_Service_Management|Systemd and Service Management]].
    - **Targets**: Collective states (e.g., `multi-user.target` for CLI, `graphical.target` for GUI).
    - **Speed**: Starts services as soon as their dependencies are met, often before the previous service finishes.

---

## Package Management and Linking

### The Birth of Package Managers
In the early days (and still in **Slackware**), software was distributed as source tarballs.
1.  **Manual Compilation**: `./configure && make && make install`.
2.  **Slackware Style**: Pre-compiled tarballs (`.tgz`, `.txz`) managed via `installpkg`. It does *not* natively resolve dependencies.
    - Communities built bridges like **SlackBuilds.org (SBo)**, which provide scripts to automate fetching tarballs, resolving dependencies (via tools like `sbopkg`), and compiling them into installable Slackware packages.
3.  **Modern Resolvers**: (APT, RPM/DNF) added **Dependency Resolution** over network repositories.

### Anatomy of a DEB Package
A `.deb` file (Debian/Ubuntu) is essentially an archive created using `ar` (archive). It contains:
- `control.tar.zst`: Contains metadata (mantainers, description) and crucially, a `control` file listing the exact `Depends` (dependencies) required to run the binaries.
- `data.tar.zst`: Contains the actual compiled binaries and directory structures (e.g., `/usr/bin/htop`) to be copied onto the filesystem.
When `apt update` runs, it fetches a massive `Packages.gz` from the repository server (defined in `sources.list`), which is an amalgamation of all `control` files, allowing APT to resolve dependency graphs locally before downloading any data.


### Dynamic Linking and `ldd`
Linux binaries are rarely "static." They rely on **Shared Objects (.so)**.
- **ldd**: A utility to view the shared library dependencies of a binary.
    - Example: `ldd /bin/bash` shows links to `libc.so`, `libtinfo.so`, etc.
- **ld.so**: The dynamic linker that resolves these paths at runtime.
- **Dependency Hell**: When different programs require conflicting versions of the same shared library. This led to modern solutions like **[[Virtualization_and_High_Performance_Systems|Containers (Docker)]]** or **Static Runtimes ([[Programming_Languages_Ecosystem|Go/Rust]])**. See also [[Package_Management_Paradigms|Package Management Paradigms]].

---

## Metadata
- **Source**: LNK [Akitando #127](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%20127%20-%20Como%20Funciona%20O%20Boot%20De%20Um%20Linux%20O%20Que%20Tem%20Num%20Livecd.md), [Akitando #128](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%20128%20-%20Entendendo%20Pacotes%20Com%20Slackware.md)
- **Status**: #ingested

## Distribution Philosophies
- **Rolling Release (e.g., Arch Linux, Manjaro)**: Continuous updates. No "major versions"; the system is always at the latest version of all packages. See [[Linux_Distribution_Philosophies|Linux Distribution Philosophies]].
- **Stable/LTS (e.g., Ubuntu, Debian, CentOS)**: Focus on reliability. Packages are frozen at specific versions, and only security patches are backported.
