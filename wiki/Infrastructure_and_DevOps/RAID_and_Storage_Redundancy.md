---
tags: [infrastructure, devops, storage, raid]
date_created: 2026-04-12
source: "[[Detecção e Correção de Erros ｜ Introdução a Redes Parte 2]]"
---
# RAID and Storage Redundancy

Disk storage arrays rely on redundancy topologies, typically configured via **RAID** (Redundant Array of Independent Disks), balancing performance against fault tolerance.

## Advanced Redundancy Models

### Synology Hybrid RAID (SHR)
Classic RAID (5/6) requires all disks to be the same size. If you mix a 10TB drive with a 4TB drive, the extra 6TB is wasted. 
- **SHR Advantage**: Uses a proprietary software layer to combine disks of different sizes, maximizing usable space while maintaining redundancy.
- **Hot Spare**: A physical disk that remains unallocated in the array. If an active drive fails, the NAS automatically activates the hot spare, rebuilding the data without human intervention.

## Hardware Foundations for High-Performance NAS

### 1. ECC RAM (Error Correction Code)
Critical for servers that manage file systems like ZFS or RAID. Bit flips in RAM (caused by cosmic rays or electrical noise) can be written to disk, corrupting the entire array. ECC RAM detects and fixes these flips in real-time.

### 2. NVMe Caching
Using high-speed NVMe SSDs to store "hot" data (frequently accessed blocks). This improves **IOPS** (Input/Output Operations Per Second), making the slow mechanical HDDs feel as fast as an SSD for common tasks.

### 3. Networking: The 10GbE Standard
To edit video (like 4K RAW or DNxHR) directly from a NAS, standard 1Gbps (125 MB/s) is a bottleneck.
- **10GbE (10 Gigabits)**: Offers up to 1.25 GB/s. This matches or exceeds the internal speeds of a high-performance HDD array (roughly 100-200 MB/s per drive).
- **Backplane Capacity**: Switches must have enough internal bandwidth to handle simultaneous 10GbE traffic across all ports without overheating or dropping packets.

## Data Preservation: Scrubbing vs. [[Bit_Rot|Bit Rot]]
**Scrubbing** is a proactive maintenance task where the NAS reads every single block of data and compares it to a master checksum.
- **[[Bit_Rot|Bit Rot]]**: Silent data corruption where a bit on the disk flips over time.
- **Healing**: If the checksum doesn't match, the system uses the parity data (from the RAID redundancy) to rewrite the correct bit, "healing" the file before you ever try to open it.
