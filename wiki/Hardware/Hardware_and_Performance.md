---
tags: [hardware, performance, virtualization, cpu]
date_created: 2026-04-12
sources:
  - "[[Akitando 137 - Games em Máquina Virtual com GPU Passthrough | Entendendo QEMU, KVM, Libvirt]] (Clipper)"
---
# Hardware and Performance

Deep technical performance optimization requires understanding the physical topology of the hardware and how the kernel schedules workloads across its resources.

## CPU Topology and Pinning
Modern CPUs are not monolithic, but composed of multiple **cores** and **threads** (Hyper-Threading). Efficient virtualization requires mapping virtual CPUs (vCPUs) to physical threads in a way that respects the hardware's internal structure.

### Cache Localization (L3 Cache)
- **Hierarchy**: L1 and L2 caches are typically private to a core. The **L3 Cache** is shared among a group of cores (e.g., 8 cores sharing 32MB of L3 in an AMD Ryzen 9).
- **Context Switching Penalty**: If a thread moves from a core in one L3 group to a core in another, the entire context must be copied between caches, causing a significant performance "hiccup."
- **Pinning Strategy**: Group vCPUs within the same physical L3 cache boundary to ensure data locality and minimize memory latency.

### CPU Isolation via Cgroups
To prevent the Host OS from interfering with high-performance Guest workloads (e.g., gaming VMs), you can "hide" cores from the host scheduler:
- **AllowedCPUs**: Using SystemD properties to set `AllowedCPUs` on `system.slice`, `user.slice`, and `init.scope`.
- **Hooks**: Automating this process via Libvirt hooks (`/etc/libvirt/hooks/qemu`) so cores are isolated only when the VM is active and released when it stops.

## Hardware Control and Automation
Advanced setups often involve controlling physical hardware properties from within the OS.

### Display Control (DDC/CI)
**DDC/CI (Display Data Channel / Command Interface)** allows software to send commands to a monitor (change brightness, contrast, or input sources) via the video cable.
- **Tooling**: `ddcutil` on Linux.
- **Automation**: Switching monitor inputs automatically when a VM starts (e.g., switching from the Host's AMD GPU output to the Guest's NVIDIA GPU output).

### CPU Governors
The kernel's "Governor" decides how to balance power consumption vs. performance.
- **Powersave/Balance**: Default for laptops/general use.
- **Performance**: Forces higher clock speeds and reduces latency.
- **Tooling**: `cpupower frequency-set -g performance`.


## Storage Media and Performance
Storage performance is determined by the physical media type and the overhead of the communication protocol.

| Technology | Average Bandwidth | Seek Latency | Description |
| :--- | :--- | :--- | :--- |
| **HDD (Mechanical)** | ~50-150 MB/s | High (ms) | High overhead due to physical head movement (Seek Time). |
| **SSD (SATA III)** | ~500-600 MB/s | Low (µs) | Limited by legacy SATA interface. |
| **NVMe (PCIe 4.0)** | ~3000-7000 MB/s | Very Low (ns) | Massive parallel lanes, minimal protocol overhead. |

### Caching and Data Integrity
Modern performance relies heavily on volatile caches (RAM) at multiple levels:
- **OS Page Cache**: Linux keeps frequently accessed sectors in RAM.
- **Drive Cache**: HDDs and SSDs have onboard RAM (e.g., 256MB) to reorder operations and hide latency.
- **Risk**: Power loss while data is in a volatile cache can lead to corruption. **Copy-on-Write (CoW)** filesystems like ZFS/Btrfs mitigate this by never overwriting active data.

### NAND Durability (PE Cycles)
SSD performance and lifespan are defined by the bits-per-cell:
- **SLC**: 1 bit (Fastest/Longest life).
- **QLC**: 4 bits (Slowest/Shortest life but cheaper).

### Paravirtualization (VirtIO)
Standardized drivers that allow a Guest OS to "collaborate" with the Hypervisor for high-speed I/O (VirtIO-Block), rather than relying on slow software emulation of legacy physical devices (IDE/SATA/E1000).
