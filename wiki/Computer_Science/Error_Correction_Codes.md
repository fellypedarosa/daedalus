---
tags: [computer science, algorithms, networking]
date_created: 2026-04-12
source: "[[Detecção e Correção de Erros ｜ Introdução a Redes Parte 2]]"
---
# Error Correction Codes (ECC)

Data transmitted via networks or stored electromagnetically is constantly liable to corruption (such as [[Bit_Rot|Bit Rot]]). Computer Science relies heavily on detection and correction codes to silently manage this hostility.

## Detection vs Correction
- **Detection (e.g., Checksums, SHA-1)**: Validates if a block of data is intact. If tampering or rot is detected, the system discards the payload. In networking, correcting errors is often too expensive computationally, so a `NAK` (Negative Acknowledgement) sequence is fired to request a packet retransmission instead.
- **Correction**: Vital for local storage where requesting a "new copy" isn't possible.

## Key Mechanisms

### Hamming Code
Created by Richard Hamming, this ingenious algorithm groups bits and calculates multiple parities mapping intersections. 
- **The Binary Search Principle**: It applies a binary search topology to single out the exact position of a bit flip. By checking overlapping parity sets, the system can determine precisely which bit is corrupted without re-reading the entire block.
- **Hardware Integration**: This is the foundation of **ECC RAM**. A single bit flip is corrected silently; a double bit flip is detected (and usually crashes the system to prevent data corruption).

### Reed-Solomon Code
An advanced correction cipher used where data corruption happens in "bursts" (consecutive bits).
- **Applications**: Mandatory for optical mediums (CDs, Blu-Rays) where scratches or dust destroy large chunks of physical data, and in deep-space communication (e.g., Voyager) where signal-to-noise ratios are extremely low.
- **Legacy Software**: Used in `PAR2` files for Usenet binary recovery.

## [[Bit_Rot|Bit Rot]] and Scrubbing
**[[Bit_Rot|Bit Rot]]** (or Silent Data Corruption) occurs when the physical medium fails or external factors (like raios cósmicos) flip a bit.
- **Single Event Upsets (SEU)**: High-altitude flights or space missions are particularly vulnerable to bit flips caused by cosmic rays.
- **Data Scrubbing**: Modern filesystems like **ZFS** and **Btrfs** perform "scrubbing"—periodically reading all data and comparing it against known checksums to proactively repair [[Bit_Rot|bit rot]] before it accumulates beyond the capacity of recovery algorithms.

## Case Studies: The 4096 Error
- **2003 Belgian Election**: A candidate in Schaerbeek received exactly 4,096 more votes than physical reality allowed. 
- **Cause**: A bit flip occurred in the 13th bit of the computer memory (2^12 = 4,096). This "impossible" number was a perfect powers-of-two match, proving that silent corruption can have real-world democratic consequences.
- **SM64 Speedrunning**: A famous case where a "glitch" that moved Mario to a higher floor was later attributed to a bit flip in the memory address storing Mario's height.
