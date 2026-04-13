---
tags: [infrastructure, virtualization, kvm, gpu_passthrough]
date_created: 2026-04-12
---
# Virtualization and High-Performance Systems

Modern virtualization has evolved from slow software emulation to near-native hardware execution through the combination of advanced kernel features and [[Hardware_Architecture|hardware support]].

## The Virtualization Stack (Linux)

### QEMU (Emulator)
A generic and open-source machine emulator and virtualizer.
- **Role**: Emulates hardware devices (disk controllers, network cards, video cards). 
- **Standalone**: Can run without KVM, but it is slow because it performs [[Compiler_Design#Emulation and Binary Translation|binary translation]] in software.

### KVM (Kernel-based Virtual Machine)
A kernel module that turns the Linux kernel into a **Hypervisor**.
- **Role**: Allows a user-space program (like QEMU) to access the virtualization features of the CPU (Intel VT-x or AMD-V). See [[Hardware_Architecture|Hardware Architecture]] for CPU internals.
- **Efficiency**: The guest OS runs instructions directly on the host CPU at native speed.

### Libvirt (API and Daemon)
A toolkit to manage virtualization platforms.
- **Role**: Provides a standard XML configuration and API to manage VMs across different backends (QEMU, Xen, LXC).
- **Tools**: `virsh` (CLI) and `virt-manager` (GUI).

---

## Containers vs VMs: The Illusion of Virtualization

While VMs utilize hypervisors to emulate entire hardware stacks and boot independent kernels, **Containers** are merely isolated native processes sharing the *host's* kernel (see [[Container_Orchestration|Container Orchestration]] for production deployments). They achieve an illusion of virtualization through two fundamental [[Linux_Internals_and_FHS|Linux kernel]] features:

### 1. Control Groups (`cgroups`)
Limit and isolate resource usage (CPU, Memory, Disk I/O) for a collection of processes.
- **Mechanism**: Grouped in hierarchies (e.g., `system.slice`, `user.slice`).
- **DoS Prevention**: By throttling a container's CPU/RAM allocation, it prevents a single runaway process from locking up the host kernel. See also [[Operating_System_Security|OS Security]].
- **Inspection**: `ls /sys/fs/cgroup`.

### 2. Namespaces (`unshare`)
Partition kernel resources such that one set of processes sees one set of resources while another set of processes sees a different set. They limit what a process can *see*.
- **PID Namespace**: Process IDs inside a container start at `1`, but are mapped to higher PIDs globally on the host. The container thinks it's alone.
- **Mount Namespace**: Replaces the global filesystem root with a fake root (e.g., a tarball extracted in `/tmp/rootfs`). Related: [[Storage_and_Filesystems|Filesystems]].
- **Network / UTS / IPC**: Virtualizes network interfaces, hostnames (`UTS`), and inter-process communication queues.

### Container Runtimes (RunC vs Containerd)
Because containers are native Linux processes, **MacOS and Windows cannot run native Docker**. They must first boot a hidden Linux VM (via Hyper-V or Hypervisor.framework) which costs performance.
- **RunC**: The core OCI (Open Container Initiative) standard runtime. It natively utilizes `cgroups` and `namespaces` (used by Podman and [[Container_Orchestration|Kubernetes]]). Can run "rootless".
- **Containerd**: A higher-level daemon (relied upon by Docker) that requires root privileges, orchestrating image pulling, storage, and networking over RunC.


## High-Performance Optimization

To achieve performance suitable for gaming or heavy compute in a VM, simple virtualization is insufficient.

### PCI Passthrough (VFIO)
Allows a guest VM to take direct control of a physical PCI device (e.g., a GPU).
- **IOMMU (Input-Output Memory Management Unit)**: A hardware feature (Intel VT-d/AMD-Vi) that isolates devices into **IOMMU Groups**.
- **Isolation**: To pass a GPU to a VM, it and its associated audio controller must be in an isolated IOMMU group.
- **VFIO Driver**: The host detaches the device and binds it to the `vfio-pci` driver, allowing the VM to "see" and control the hardware directly.

### CPU Pinning
Ensures that virtual CPUs (vCPUs) are always executed on the same physical CPU threads. Related: [[Concurrency_and_Parallelism|Concurrency and Parallelism]].
- **Cache Locality**: Prevents the performance hit caused by the kernel moving a vCPU thread from one physical core to another (which flushes the CPU cache). See [[Hardware_Architecture#Cache Hierarchy|Cache Hierarchy]].
- **Isolcpus**: Host kernel parameter to reserve specific cores exclusively for the VM.

### VirtIO drivers
Standardized interface for virtual devices.
- **Mechanism**: Instead of emulating a complex physical device (like an IDE disk), the guest uses a simplified "VirtIO" driver that communicates efficiently with the host's hypervisor.

---

## Use Cases: GPU Passthrough Gaming

By using **QEMU + KVM + VFIO**, it is possible to run a Windows VM inside Linux with a dedicated GPU.
- **Near-Native Performance**: Typical overhead is <5%.
- **Requirements**: Two GPUs (one for the host Linux, one for the guest Windows), a monitor with multiple inputs or a KVM switch, and a CPU with IOMMU support.

---

## Metadata
- **Source**: LNK [Akitando #137](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%20137%20-%20Games%20em%20M%C3%A1quina%20Virtual%20com%20GPU%20Passthrough%20%20Entendendo%20QEMU,%20KVM,%20Libvirt.md)
- **Status**: #ingested
