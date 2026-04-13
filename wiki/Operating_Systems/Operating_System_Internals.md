---
tags: [operating_systems, internals, windows_nt, history]
date_created: 2026-04-12
sources:
  - "[[Akitando 60 - Entendendo WSL 2 | E uma curta história sobre Windows NT]] (Clipper)"
  - "[[Akitando 139 - Entendendo Como Containers Funcionam]] (Clipper)"
---
# Operating System Internals

System architecture and the internal mechanics of kernels determine how software interacts with hardware and how different operating systems can simulate or "host" each other.

## Windows NT: The "New Technology" Legacy
Windows NT (New Technology) was designed from the ground up to be a portable, multi-user, and multi-processor operating system, led by **Dave Cutler** (formerly of DEC/VMS).

### Architectural Key Concepts
- **HAL (Hardware Abstraction Layer)**: A thin layer of software that hides hardware differences from the kernel, allowing NT to run on various architectures (x86, MIPS, Alpha, PowerPC).
- **Object Manager**: Internally, NT treats all resources (files, threads, synchronization primitives) as "Objects" managed by a centralized Executive layer.
- **Subsystem Personalities**: NT was designed to host multiple "personalities" via subsystems. Initially, it supported:
    - **Win32**: The primary personality.
    - **POSIX.1**: Required for government contracts, allowing UNIX source code to be compiled on NT.
    - **OS/2**: Compatibility for applications from the IBM/Microsoft partnership.
- **Micro-kernel vs. Monolithic**: While initially inspired by the **Mach micro-kernel** (running drivers in user mode/Ring-3), performance requirements forced many drivers (Video, Printing, and even parts of the IIS HTTP stack) into the kernel mode (Ring-0) in later versions like NT 4.0. See [[Operating_Systems_History|OS History]] for the broader context.

## Hardware Abstraction and Privileges

The CPU manages execution via levels of privilege to protect system stability and security.

### Protection Rings (x86 Architecture)
Modern CPUs implement hierarchical protection domains, commonly referred to as Rings. See [[Hardware_Architecture|Hardware Architecture]] for the physical CPU structure:
- **Ring 0 (Kernel Mode)**: The most privileged level. The Kernel has direct, unrestricted access to hardware (CPU, Memory, I/O devices).
- **Ring 1 & 2**: Historically intended for drivers and virtualization (hypervisors), but often unused or repurposed (e.g., VirtualBox using Ring 1 for guest OS isolation).
- **Ring 3 (User Mode)**: Where application code executes. Access to hardware is restricted; any hardware interaction (writing to disk, sending a network packet) must be requested via a **Syscall** to the Kernel.
    - **Syscall Overhead**: Jumping from Ring 3 to Ring 0 involves a "trap" or interrupt, saving CPU state (registers), switching stacks, and verifying permissions. This context switch into Kernel space is technically expensive (microseconds) and becomes a bottleneck in high-throughput applications.

### ARM Exception Levels (EL)
In the ARM architecture, similar concepts exist as Exception Levels:
- **EL0**: User Land (equivalent to Ring 3).
- **EL1**: Kernel Space (equivalent to Ring 1/0).
- **EL2**: Hypervisor layer.
- **EL3**: Secure Monitor (highest privilege).

## Linux Kernel Primitives for Isolation
Containers (and modern service isolation) rely on specific kernel features to "lie" to processes about their environment and restrict their resource consumption. See [[Virtualization_and_High_Performance_Systems|Virtualization]] and [[Container_Orchestration|Container Orchestration]] for how these primitives enable Docker and Kubernetes.

### Namespaces (The "Matrix")
Namespaces allow the kernel to provide different views of system resources to different processes.
- **PID (Process ID)**: Isolates the process ID space. A process in a PID namespace sees itself as PID 1, and cannot see processes in parent or sibling namespaces.
- **UTS (Unix Timesharing System)**: Allows a process to have its own hostname and domain name.
- **Network (net)**: Provides isolated network stacks (interfaces, IP addresses, routing tables, port bindings).
- **Mount (mnt)**: Provides isolated mount points, similar to a more robust `chroot`. See [[Linux_Internals_and_FHS|Linux FHS]].
- **IPC (Inter-Process Communication)**: Isolates System V IPC objects and POSIX message queues.
- **User (user)**: Maps user/group IDs within a namespace to different IDs on the host (e.g., being `root` inside a container while being an unprivileged user on the host).

### Cgroups (Control Groups)
Managed via the virtual filesystem at `/sys/fs/cgroup`, cgroups handle resource accounting and limiting.
- **Hierarchy**: Organized in "slices" (e.g., `system.slice`, `user.slice`). Sub-groups inherit limits from parents.
- **Quotas**: Allows setting specific limits (e.g., `CPUQuota=30%`, `MemoryLimit=2G`) to prevent **Denial of Service (DoS)** by rogue or resource-heavy processes (like Matlab or complex builds).

### Linux Capabilities
Finer-grained control over traditional "root" privileges. Instead of an all-or-nothing binary (root vs. non-root), privileges are broken down into specific capabilities.
- **Examples**: 
    - `CAP_NET_BIND_SERVICE`: Allows binding to ports < 1024 without being full root.
    - `CAP_KILL`: Allows sending signals (SIGKILL, SIGTERM) to processes.
- **Management**: Controlled via `setcap` on files and `capsh` for shell environments. Stored as bitsets in the kernel's process object.

### Seccomp (Secure Computing Mode)
A kernel feature that allows filtering the syscalls a process can make. Using BPF (Berkeley Packet Filter), the kernel can deny or kill processes that attempt unauthorized syscalls, significantly reducing the attack surface. See [[Operating_System_Security|OS Security]] and [[Firewalls_and_Proxies|Firewalls]].

## Process Abstractions
### Pico Processes (WSL 1)
Stemming from Microsoft Research's **Project Drawbridge**, Pico processes are "minimal" processes with zero host OS interference (clean address space).
- **The Wrapper Pattern**: A Pico process is associated with a kernel driver (e.g., LXCore.sys) that intercepts syscalls from a different binary format (ELF64) and translates them into host-native syscalls (NT).
- **Semantic Mapping**: Problems arise when one OS has primitives that simply don't exist in the other (e.g., mapping Linux's `fork` or directory structures like `/proc` and `/sys` to NT counterparts).

### Subsystems and "Personalities"
The concept of subsystems allows a kernel to provide different API surfaces.
- **Xenix**: Microsoft's early 1980s UNIX (v7 derivative) which shared many concepts later integrated into NT.
- **Interix (SFU)**: A later iteration of the POSIX subsystem that provided a more complete UNIX-like environment on Windows than the original minimal POSIX.1 implementation.

## Multitasking and Scheduling

Operating systems manage how the CPU is shared among multiple execution units.

### Multitasking Models
- **Cooperative Multitasking**: Older systems (like Windows 3.1) relied on applications to voluntarily yield control back to the OS. If a program hung or failed to yield (e.g., during a long printing job), the entire system froze.
- **Preemptive Multitasking**: Modern systems (OS/2, Win95, Linux, NT) use a hardware-timer-driven **Scheduler**. The OS forces context switches regardless of the application's state, ensuring system responsiveness.

### Linux Schedulers
- **Completely Fair Scheduler (CFS)**: Introduced in Linux kernel 2.6.23 (2007). It implements a red-black tree algorithm to ensure $O(\log n)$ efficiency in task selection. It aims to give equal CPU time to all tasks based on "virtual runtime," prioritizing interactive tasks that sleep often over CPU-bound tasks.
- **NPTL (Native POSIX Thread Library)**: Prior to NPTL, Linux threads (LinuxThreads) were inefficient. NPTL introduced a 1:1 mapping between User-space threads and Kernel-space execution units, correcting signal handling and synchronization issues.

## Concurrency and I/O Strategy

How a kernel manages execution units and data waiting periods significantly affects application performance and resource utilization.

### Execution Units: Threads vs. Fibers
- **Kernel Threads**: Managed by the OS scheduler.
    - **Context Switching**: Changing from one thread to another requires a transition to kernel mode, saving/restoring CPU registers, and updating memory maps. This overhead is measured in microseconds—expensive when scaled to thousands of units.
    - **Safety**: Thread-safe pools are required if shared by multiple threads (e.g., a Database pool shared by multiple native worker threads).
- **Fibers (User-space Threads / Co-routines)**: Managed by the application runtime (e.g., Crystal, Go, Kotlin Coroutines). See [[Concurrency_and_Parallelism|Concurrency and Parallelism]] for the Actor Model and CSP.
    - **Efficiency**: Context switching happens in user space without kernel participation, minimizing overhead.
    - **Throughput**: Allows a single kernel thread to handle thousands of "concurrent" fibers by yielding execution whenever one fiber is waiting for I/O.

### I/O Wait Stratagems
- **Synchronous (Blocking)**: The thread stops execution and enters a "wait state" until the I/O operation (disk/network) is complete. While simple to program, it wastes CPU cycles and limits concurrency per thread.
- **Asynchronous (Non-blocking / Reactor Pattern)**: The application initiates an I/O request and continues execution. When the I/O is ready, the kernel notifies the application.
    - **Kernel Primitives**:
        - **epoll (Linux)**: Scalable I/O event notification. Unlike the older `select` (which scans all sockets), `epoll` is $O(1)$ regarding the number of monitored descriptors.
        - **kqueue (BSD/macOS)**: Similar to epoll, providing high-performance event notification.
        - **IOCP (I/O Completion Ports - Windows)**: A highly scalable multi-threaded I/O model where the system handles the completion of I/O operations and notifies worker threads.
    - **Reactor Pattern**: Used by runtimes like Node.js (Libuv) or NGINX (Igor Sysoev). A single-threaded event loop (Reactor) manages thousands of concurrent I/O operations without the overhead of per-connection threads. See [[Web_Architecture_and_Scalability|Web Architecture]].

## [[Memory_Management|Memory Management]]
For a detailed analysis of physical memory, virtual address spaces, and allocators, see [[Memory_Management]].
