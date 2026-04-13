---
tags: [infrastructure, devops, virtualization]
date_created: 2026-04-12
sources:
  - "[[Akitando 47 - Entendendo Devops para Iniciantes em Programação (Parte 1)  Série Começando aos 40]] (Clipper)"
  - "[[Akitando 48 - Entendendo Devops para Iniciantes em Programação (Parte 2)  Série Começando aos 40]] (Clipper)"
  - "[[Akitando 60 - Entendendo WSL 2 | E uma curta história sobre Windows NT]] (Clipper)"
  - "[[Akitando 137 - Games em Máquina Virtual com GPU Passthrough | Entendendo QEMU, KVM, Libvirt]] (Clipper)"
  - "[[Akitando 139 - Entendendo Como Containers Funcionam]] (Clipper)"
---
# Virtualization and Hypervisors

Virtualization allows multiple isolated Operating Systems to run on a single physical host by abstracting the underlying hardware resources (CPU, RAM, Disk).

## VMs vs. Containers: The Core Distinction
While both provide isolation, they operate at different layers of the system stack.

| Feature | Virtual Machines (VMs) | Containers |
| :--- | :--- | :--- |
| **Kernel** | Runs a **new** guest kernel | Shares the **host** kernel |
| **Architecture** | Can emulate different archs (via QEMU) | Must match host architecture |
| **Overhead** | High (full OS boot, virtual hardware) | Low (process-level isolation) |
| **Startup** | Minutes/Seconds | Sub-second (native execution) |
| **Isolation** | Hardware-level (Hypervisor boundary) | Kernel-level (Namespaces/Cgroups) |

> [!IMPORTANT]
> **The Non-Linux Reality**: Because containers rely on Linux-specific kernel primitives (Namespaces/Cgroups), running Docker on **macOS** or **Windows** requires a lightweight Linux VM (using Hyper-V or Hypervisor.framework) to act as the actual container host. This is why Docker is inherently more resource-intensive on these platforms compared to native Linux.

## Hypervisor Classifications
The hypervisor is the software layer that manages virtual machine (VM) lifecycle and resource allocation.

### Type 1: Bare Metal
The hypervisor runs directly on the hardware with no underlying host OS.
- **Examples**: VMware ESXi, Microsoft Hyper-V, Xen.
- **Performance**: Near-native efficiency, common in data centers.

### Type 2: Hosted
The hypervisor runs as an application on top of an existing Operating System (Windows, Linux, macOS).
- **Examples**: VirtualBox, VMware Workstation, KVM (integrated into Linux).
- **Usage**: Local development environments and testing.

## Windows Subsystem for Linux (WSL)
The evolution of WSL highlights the shift from syscall translation to true virtualization.
- **WSL 1 (Syscall Translation)**: Based on **Project Drawbridge**, it used **Pico Processes**—minimal processes with zero OS interference—to run unmodified Linux ELF64 binaries.
    - **Mechanism**: A driver (LXSS.sys) acted as a translation layer, mapping Linux syscalls (e.g., `fork`, `open`) to Windows NT equivalents (e.g., `NtCreateProcess`).
    - **Performance**: Near-native for CPU-bound tasks, but extremely slow for I/O due to the overhead of the **Virtual File System (VFS)** translating EXT4 semantics over NTFS and constant interference from Windows Defender.
- **WSL 2 (Hyper-V Utility VM)**: Uses a real, Microsoft-shipped Linux kernel (GPL-compliant fork) running in a lightweight, dynamically-allocated VM.
    - **Boot Sequence**: Boots in ~1 second by using a memory dump (similar to a VM snapshot), bypassing the "cold boot" cycle.
    - **Filesystem (9P Protocol)**: To allow Windows to access Linux files and vice-versa, WSL2 uses the **9P protocol** (originally from **Plan 9 from Bell Labs**). It acts as a lightweight network filesystem that exposes the Linux VHD to Windows.
    - **I/O Efficiency**: Since Linux is writing to a virtual disk (VHDX) instead of translating over NTFS, I/O performance is orders of magnitude faster in WSL2.
    - **Network (NAT)**: Unlike WSL1 (which shared the host IP), WSL2 operates as a separate VM with its own internal network, requiring NAT and port-forwarding to bridge to the Windows host.

## Advanced Virtualization: PCI Passthrough (VFIO)
To achieve near-native performance for GPU-bound tasks (e.g., gaming, Machine Learning), hardware can be passed directly to the Guest OS.
- **IOMMU (VT-d/AMD-Vi)**: A hardware feature that allows the CPU to map virtual memory addresses to physical I/O devices. Hardware must be isolated into unique IOMMU groups.
- **VFIO (Virtual Function I/O)**: A Linux kernel framework for exposing direct device access to userspace (QEMU). It uses a "stub" driver to prevent the Host OS from claiming the device.
- **The KVM/QEMU/Libvirt Stack**:
    - **QEMU**: The emulator/userspace process that simulates the hardware and performs dynamic binary translation.
    - **KVM (Kernel Virtual Machine)**: The Linux kernel module that acts as a Type 1.5 hypervisor, providing hardware acceleration.
    - **Libvirt**: An open-source API and management daemon for controlling multiple hypervisors (QEMU, Xen, etc.) via tools like `virsh` or `virt-manager`.

## Paravirtualization and VirtIO
In paravirtualization, the Guest OS is "aware" it is virtualized and uses specialized drivers to reduce overhead.
- **VirtIO**: A standardized interface for virtual devices (Disk, Network, Serial).
- **Efficiency**: Avoids the cost of full hardware emulation by using high-speed shared memory rings for I/O operations.

## The Transformation to Infrastructure as Code (IaC)
Modern DevOps shifted from manual "Colocation" and physical server rack management to cloud-based virtualization (IaaS) provided by vendors like **AWS**, **GCP**, and **Azure**, where compute power is provisioned via APIs.
