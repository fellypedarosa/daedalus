---
tags: [infrastructure, linux, storage, recovery]
date_created: 2026-04-12
sources: 
  - "[[Protegendo e Recuperando Dados Perdidos - Git, Backup, BTRFS]] (YouTube)"
  - "[[Akitando 146 - Protegendo e Recuperando Dados Perdidos - Git, Backup, BTRFS]] (Clipper)"
---
# Disaster Recovery and File Systems

The integrity of a system relies on the architecture of its filesystem. Understanding the abstraction gap between physical storage and logical maps allows for both data salvage and proactive resilience.

## Modern Filesystem Paradigms: BTRFS & CoW

Unlike legacy filesystems (Ext4), **BTRFS** (B-Tree File System) is designed for high-fidelity data integrity and volume management using **Copy-on-Write (CoW)**.

### Copy-on-Write (CoW) Mechanics
- **Mechanism**: When a file is modified, the filesystem does not overwrite the existing data blocks. Instead, it writes a new block with the updated data and updates the pointer to the new block.
- **Atomic Operations**: Since the old pointer remains valid until the new block is successfully written, the operation is atomic—a crash mid-write doesn't leave the file corrupted.
- **Snapshots**: By simply "freezing" the pointers at a specific moment, BTRFS creates **Instant Snapshots**. These are essentially read-only (or read-write) subvolumes that share the same data blocks until changes occur (block-level deduplication).
- **Checksums (Scrubbing)**: BTRFS calculates checksums for every block. Periodic **Scrubbing** reads all blocks to verify checksums against the physical bitstream, identifying and—in a RAID configuration—automatically repairing **[[Bit_Rot|Bit Rot]]**.

### Subvolumes and System Rollbacks
- **Structural Layout**: Common Linux conventions use `@` for root and `@home` for home subvolumes.
- **Timeshift**: A tool that automates BTRFS snapshots before system updates.
- **`grub-btrfs`**: Allows booting directly into a previous snapshot from the GRUB menu, providing a failsafe against "broken" updates or misconfigurations.

## Data Recovery Procedures

### 1. Bit-for-Bit Imaging
Immediate isolation is critical. Use `dd` to dump a raw ISO of the corrupted volume:
`dd if=/dev/sdb of=recovery_dump.img bs=4M status=progress`

### 2. Superblock Rehabilitation
If the Superblock (the main filesystem index) is corrupted:
- **Redundant Superblocks**: Most filesystems intersperse backup superblocks.
- **Recovery**: Use `e2fsck -b <block_number>` for Ext4 or `btrfs rescue super-recover` for BTRFS.

### 3. Forensic Header Scraping
When structural indices are lost, tools must bypass the filesystem logic and read raw sectors:
- **TestDisk**: Recovers lost partitions and fixes partition tables.
- **PhotoRec**: A signature-based recovery tool that ignores the filesystem and searches for file headers (JPEG, ELF, PDF, ZIP).

## Multi-Tier Resilience Strategy

A robust defense requires three layers of protection:
1. **Level 1 (Git)**: Local resilience for code and configurations. Protects against accidental deletion or local logic errors.
2. **Level 2 (Snapshots/Timeshift)**: Protection against OS-level failures, ransomware, or unstable updates. Instant rollback capabilities.
3. **Level 3 (External/NAS/Offsite)**: Protection against full hardware failure or environmental disaster (Fire, Theft).

### Ransomware Defense
Read-only BTRFS snapshots are immutable via the network. If a system is hit by ransomware, the attacker can encrypt the active filesystem, but cannot modify the underlying snapshot pointers. Rollback is instantaneous.

## Reference Tools
- [TestDisk/PhotoRec](https://www.cgsecurity.org/wiki/TestDisk)
- [Btrfs documentation](https://btrfs.readthedocs.io/)
- [Snapper](http://snapper.io/) (OpenSUSE style snapshot management)
