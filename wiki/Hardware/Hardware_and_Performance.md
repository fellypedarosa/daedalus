---
tags: [hardware, performance, virtualization, cpu]
date_created: 2026-04-12
sources:
  - "[[Akitando 137 - Games em Máquina Virtual com GPU Passthrough | Entendendo QEMU, KVM, Libvirt]] (Clipper)"
  - "[[Artificial_Intelligence/FABIO_AKITA_-_Flow_588.md|FABIO AKITA - Flow 588]] (Clipper)"
  - "[SUPERINTELIGÊNCIA ARTIFICIAL - Podcast 1583](file:///home/rosa/Dropbox/Daedalus/raw/youtube/cataloged/Podcast_1583_Superinteligencia.md) (Clipper)"
---
# Hardware and Performance

Deep technical performance optimization requires understanding the physical topology of the hardware and how the kernel schedules workloads across its resources.

## CPU Topology and Pinning
Modern CPUs are not monolithic, but composed of multiple **cores** and **threads** (Hyper-Threading). 

### Specialization: CPU vs. GPU
A fundamental performance distinction exists between general-purpose logic and massive parallel arithmetic:
1. **CPU (Scalar/Integer Logic)**: Designed for discrete, non-linear tasks (conditional branches, pointer manipulation). It excels at calculating one high-precision integer at a time inside a finite range (up to $2^{64}$ for 64-bit systems).
2. **GPU (Matrix/Tensor Multiplications)**: Designed for vector processing. While its individual cores are slower than a CPU's, a GPU can process millions of data points in a single instruction cycle.
    - **Tensors**: Multidimensional arrays (rank-n arrays).
    - **Inference Cost**: Running an LLM is a constant stream of matrix-to-matrix multiplications (dot products, cosine similarities). A GPU "multiplies" entire planes of data at once, whereas a CPU would need to iterate through every pixel/vector in a loop.
### Miniaturization and the 1nm Wall
Moore's Law (the doubling of transistors every 2 years) hit a physical ceiling in the early 2020s.
- **Physical Limit**: Transistors reached the **1 nanometer (1nm)** scale—roughly the width of several silicon atoms.
- **Quantum Tunneling**: Below 1nm, electrons can "leak" through insulating barriers due to quantum effects, causing cross-talk and bit flips.
- **Paradigm Shift**: Performance scaling now relies on **packaging** (3D stacking, Chiplets) and **architectural specialization** (NPU/APU) rather than pure miniaturization.

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

## AI and LLM Hardware (2026 Update)
The requirements for AI inference have shifted the focus back to memory bandwidth and total addressable RAM.

### GPU VRAM vs. Unified RAM
- **Consumer GPUs (NVIDIA RTX 5090)**: While offering the highest TFLOPS, they are bottlenecked by **VRAM** capacity (32GB as of 2026). This limits the local execution of large models (>50B parameters) without heavy quantization.
- **Unified RAM (AMD Ryzen AI Max)**: Modern APU architectures allow for a shared pool of high-speed RAM (e.g., 128GB LPDDR5x) that can be dynamically allocated to the the GPU (e.g., 96GB for VRAM). This enables running 100B+ parameter models (like Qwen 3.5) locally, albeit with lower TFLOPS than a dedicated high-end GPU.

### Inference Performance Factors
1. **Memory Bandwidth**: The primary bottleneck for LLM inference. High-speed interconnects and wide memory buses are more critical than raw compute cores for token generation speed.
2. **Quantization (INT4/INT8)**: Techniques to reduce model size to fit within available VRAM. High-performance inference engines (Llama.cpp, EXL2) optimize these operations for specific hardware instructions (AVX-512, AMX).

---
*See also*: [[Artificial_Intelligence/AI_and_LLMs.md|AI and LLMs]], [[Artificial_Intelligence/LLM_Harness_and_Reasoning.md|LLM Harness and Reasoning]]
