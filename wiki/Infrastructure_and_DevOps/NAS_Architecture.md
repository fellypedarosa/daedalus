---
tags: [hardware, networking, devops]
date_created: 2026-04-12
sources:
  - "[[Criando uma Rede Segura ｜ Introdução a Redes Parte 6 - VPN e NAS]] (YouTube)"
  - "[[Akitando 126 - Criando uma Rede Segura  Introdução a Redes Parte 6 - VPN e NAS]] (Clipper)"
---
# Network Attached Storage (NAS) Architecture

A NAS is functionally a headless PC running minimalist Linux ecosystems (like DSM or TrueNAS) designed to securely orchestrate massive disk arrays via network protocols. 

## Core Principles
- **Redundancy Models**: Typical setups leverage formats like `mdadm` or TrueNAS ZFS. Synology implements Hybrid RAID (SHR) to optimize mismatched disk capacities while hot-swapping failing sectors automatically with parity rebuilding.
- **ECC Memory Requirement**: Massive local caches mandate Error-Correcting Code (ECC) Memory (Hamming Code vectors). Standard memory degrades integrity long-term given the reality of Single Event Upsets / Bit flips driven by cosmic rays. Without it, you are vulnerable to silent data corruption.

## High Velocity Networking (10GbE)
Consumer Gigabit Ethernet maxes out around 125 Megabytes/second. 
Direct workflow rendering over NAS mandates full 10 Gigabit topology (aggregating up to ~1000 Megabytes/second). This setup demands:
- 10GbE Network Interface Cards (NICs)
- Certified Cat6A cables
- Powerful internal Switches to process bridging routing packets dynamically.
- NVMe Cache Pools mitigating random seek latencies prior to block-loading from mechanical HDDs.
