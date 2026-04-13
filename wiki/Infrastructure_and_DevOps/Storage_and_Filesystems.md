---
tags: [infrastructure, storage, filesystems, btrfs, raid]
date_created: 2026-04-12
---
# Storage Architecture and File Systems

A comprehensive overview of data persistence, spanning physical storage media, hardware abstractions, and the logical organization of file systems.

## Physical Storage Media

### HDD (Hard Disk Drive)
- **Mechanics**: Magnetic platters spinning under a moving arm with read/write heads.
- **Vulnerability**: Mechanical failure due to moving parts (motors, heads). Requires "parking" (historical practice) and stabilization.
- **Addressing**:
    - **CHS (Cylinder-Head-Sector)**: Legacy 3D coordinate system. Limited by bit-counts in BIOS/MBR (max ~8GB/2TB).
    - **LBA (Logical Block Addressing)**: Modern linear addressing (0 to N sectors). The OS sees a flat array; the drive's controller maps it to physical geometry.

### SSD & NVMe
- **SSD (SATA)**: NAND Flash in a 2.5" form factor. Limited by SATA III bandwidth (~600MB/s).
- **NVMe (PCIe)**: High-performance protocol connecting directly to PCI Express lanes (M.2 slots). Drastically lower latency and higher bandwidth (GB/s).
- **NAND Flash Types**:
    - **SLC (Single-Level Cell)**: 1 bit/cell. Most durable (~50k-100k cycles), fastest.
    - **MLC (Multi-Level Cell)**: 2 bits/cell.
    - **TLC (Triple-Level Cell)**: 3 bits/cell.
    - **QLC (Quad-Level Cell)**: 4 bits/cell. High capacity, lowest durability (~1k cycles), slowest.

## Hardware Abstractions & Redundancy

### RAID (Redundant Array of Inexpensive Disks)
- **RAID 0 (Stripping)**: Splits data across drives. High performance, zero redundancy. If one drive fails, **all data is lost**.
- **RAID 1 (Mirroring)**: Duplicate copy on second drive. Safe but uses 50% capacity.
- **RAID 5 (Parity)**: Data and parity bits distributed across 3+ drives. Can survive 1 drive failure.
- **RAID 10 (1+0)**: Mirroring + Stripping. Best of both worlds (performance + redundancy) but expensive.

### Storage Network Types
- **DAS (Direct Attached Storage)**: USB/Thunderbolt external drives.
- **NAS (Network Attached Storage)**: A dedicated server (e.g., Synology) providing file-level access over Ethernet (NFS/SMB).
- **SAN (Storage Area Network)**: Block-level storage fabric used in datacenters (e.g., AWS EBS). See [[NAS_Architecture|NAS Architecture]] for home/prosumer setups.

## Boot Architecture
- **Partition Tables**:
    - **MBR**: Legacy. Max 4 primary partitions, 2TB limit.
    - **GPT**: Modern. 128-bit GUIDs, support for massive volumes and many partitions.
- **Firmware Interface**:
    - **BIOS**: Legacy, looks for MBR.
    - **UEFI**: Modern, modular, requires **ESP (EFI System Partition)** formatted in FAT32. See [[Linux_Boot_Process|Linux Boot Process]].
    - **Secure Boot**: Verifies [[Digital_Signatures_and_GPG|digital signatures]] of bootloaders to prevent rootkits.

## File System Paradigms

### The FAT Family (File Allocation Table)
Simple, linear table. No journaling or advanced features.
- **FAT12/16/32**: 4GB file size limit on FAT32.
- **VFAT**: A hack for Long File Names (LFN) using hidden directory entries.
- **exFAT**: Modern, open standard for removable media. No 4GB limit, no journaling, universally compatible (Windows/Mac/Linux).

### Modern Filesystems
- **NTFS (Windows)**: Journaling, B+Tree indexing (see [[Database_Fundamentals#Underlying Structures|B-Trees]]), Alternate Data Streams (ADS) for hidden metadata.
- **APFS (Apple)**: Optimized for Flash. Metadata clones, snapshots, native encryption.
- **ZFS (The Zettabyte File System)**:
    - **Self-Healing**: Per-block checksums detect and repair bitrot.
    - **Pool Management**: Combines FS and Volume Manager.
    - **Copy-on-Write (CoW)**: Never overwrites data in-place.
- **Btrfs (B-Tree FS)**: Modern Linux filesystem focusing on fault tolerance and repair.

---

## Btrfs: Modern Filesystem Mechanics

Btrfs (B-Tree Filesystem) uses a **Copy-on-Write (CoW)** paradigm that differentiates it fundamentally from journaling filesystems like EXT4.

### Core Features
- **Copy-on-Write (CoW)**: Data is never overwritten. When a block is modified, a new version is written to a free block, and the metadata pointers are updated. This enables atomic operations and near-instant snapshots.
- **Checksumming**: Every data block and metadata chunk has a checksum. During a read, the system verifies the checksum, detecting "[[Bit_Rot|Bit Rot]]" (silent data corruption). See also [[Error_Correction_Codes|Error Correction Codes]].
- **Subvolumes**: Discrete filesystem trees that share the same pool of storage. For example, `@` for root and `@home` for user data can be managed and snapshotted independently.
- **Deduplication**: Identical data blocks across the filesystem can be consolidated to point to a single physical block on disk. *Note: this is not automatic.* Tools must be run to actively deduplicate.

### Maintenance and Performance
- **Scrubbing**: A background process (`btrfs scrub start`) that reads all data and verifies checksums against physical disk content to find and repair errors.
- **Reclaiming Space (Balancing)**: Unlike traditional filesystems, simply deleting files or dropping a snapshot does not instantly return the unallocated blocks to the pool. `btrfs filesystem balance start /` must be manually run to redistribute and reclaim chunk space.
- **Compression**: Transparently compresses data using algorithms like **ZSTD** or LZO (`compress-force=zstd` mount option). See [[Compression_Algorithms_and_Multimedia|Compression Algorithms]].
- **NoCOW (`chattr +C`)**: CoW can cause severe space exhaustion when combined with snapshots for large, random-write or dynamically generated files (like [[Container_Orchestration|Docker]] image layers in `/var/lib/docker` or [[Virtualization_and_High_Performance_Systems|VM]] disk images). Disabling CoW specifically for these directories prevents the snapshots from archiving temporary binary image overlaps.

### Snapshots and Restoration
- **Snapshots**: Space-efficient captures of subvolume states. Only the metadata and changed blocks consume space. They act as "commits" against the filesystem.
- **Ransomware Defense**: Local hardware snapshots are functionally read-only to malicious userspace processes. See [[Malware_and_Ransomware_Defenses|Malware and Ransomware Defenses]].
- **Timeshift**: A popular tool for managing system snapshots. Combined with **grub-btrfs**, it allows a user to boot directly into a snapshot from the GRUB menu if a system update (e.g., a broken kernel) bricks the installation.


---

## Data Recovery Techniques

When a filesystem is corrupted beyond standard mounting, several levels of recovery exist:

### EXT4 Superblock Recovery
If the primary superblock is corrupted, EXT4 maintains backup copies.
- `dumpe2fs /dev/sdX | grep -i superblock`: Locates backup superblocks.
- `fsck -b <block_number> /dev/sdX`: Attempts to repair the filesystem using a backup superblock.

### Data Carving (Last Resort)
When the metadata/index of the filesystem is completely lost, tools must scan raw sectors for file signatures ([[Digital_Formats_and_Encodings|Magic Numbers]]).
- **PhotoRec**: Scans disk headers for bit patterns (e.g., `FF D8 FF E0` for JPEG) to reconstruct files without their names. See [[Disaster_Recovery_and_File_Systems|Disaster Recovery]].
- **TestDisk**: Attempts to recover deleted partitions and fix partition tables.

### Data Protection Philosophy
- **Git as Decentralized Backup**: [[Git_and_Version_Control|Git]] is fundamentally a decentralized object tracker. Even without GitHub, making frequent commits provides a pristine undo log. See [[Local_Git_Resilience|Local Git Resilience]] and [[Git_Algorithms_and_Internals|Git Internals]].


---

## Data Persistence & Safety
- **Character vs. Block Devices**:
    - **Block Devices**: Read/write in fixed-size chunks (sectors/clusters). OS uses RAM cache for performance.
    - **Character (Raw) Devices**: Byte-by-byte streaming. Used for low-latency (Keyboards) or when the app manages its own cache.
- **Caching Risks**: Data in RAM cache is volatile. Power loss during write-back can cause corruption unless using CoW or UPS/BBU (Battery Backup Unit).

---

## Metadata
- **Source**: LNK [Akitando #99](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%2099%20-%20Quebrei%203%20HDs%20Entendendo%20Armazenamento.md), [Akitando #101](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%20101%20Tudo%20que%20Voc%C3%AA%20Queria%20Saber%20Sobre%20Dispositivos%20de%20Armazenamento.md), [Akitando #102](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%20102%20-%20Entendendo%20Sistemas%20de%20Arquivos%20FAT.md), [Akitando #103](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%20103%20-%20Todos%20os%20Sistemas%20de%20Arquivos%20de%20FAT%20a%20ZFS.md), [Akitando #146](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%20146%20-%20Protegendo%20e%20Recuperando%20Dados%20Perdidos%20-%20Git,%20Backup,%20BTRFS.md)
- **Status**: #ingested
