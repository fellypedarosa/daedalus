---
tags: [memory_management, computer_science, operating_systems, garbage_collection, internals]
date_created: 2026-04-12
sources:
  - "[[Akitando 45 - Gerenciamento de Memória (Parte 1) | Entendendo Back-end para Iniciantes (Parte 5)]] (Clipper)"
  - "[[Akitando 46 - Gerenciamento de Memória (Parte 2) | Entendendo Back-end para Iniciantes (Parte 6)]] (Clipper)"
---

# Memory Management

Memory management is the bridge between the physical constraints of hardware and the abstract data structures of software. Efficient management is critical for performance, stability, and handling high-concurrency environments.

## Hardware Foundations

The performance of memory is governed by its proximity to the CPU and its physical architecture.

### Memory Hierarchy
1.  **CPU Caches (L1, L2, L3)**: Integrated into the CPU chip. Extremely fast but limited in size (MBs). See [[Hardware_Architecture|Hardware Architecture]].
2.  **RAM (Random Access Memory)**: Main memory. Slower than cache but larger (GBs).
    - **DDR (Double Data Rate)**: Transfers data on both the rising and falling edges of the clock signal.
    - **ECC (Error Correcting Code)**: Specialized memory that can detect and fix single-bit data corruption, essential for mission-critical servers. See [[Error_Correction_Codes|Error Correction]].
3.  **Storage / SWAP (SSD/HDD)**: Used when RAM is exhausted. Orders of magnitude slower than RAM.

### Address Space
- **32-bit Architecture**: Limited to $2^{32}$ (4GB) of addressable memory. **PAE (Physical Address Extension)** allowed systems to see more RAM (64GB+), but individual processes were still restricted to a 4GB virtual space.
- **64-bit Architecture**: Theoretically addresses $2^{64}$ (16 EB). Practical limits are usually 48-bit (256TB) due to hardware implementation (barrettes).

## Virtual Memory and Isolation

[[Operating_System_Internals|OS kernels]] use **Virtual Memory** to provide each process with its own private, contiguous address space (e.g., `0x00` to `0xFF`).

- **Mapping**: The kernel maps virtual addresses to physical RAM pages using page tables. This provides process isolation; one process cannot accidentally access another's memory.
- **Memory Reservation**: In older systems (like 32-bit Windows), the space was often split (e.g., 2GB for User space, 2GB for Kernel space).
- **OOM Killer (Out of Memory Killer)**: A Linux/Unix mechanism that monitors RAM usage. When exhausted, it kills processes (often the most resource-heavy ones) to prevent a total system crash.

## Memory Allocators

Allocators manage how a process requests and releases memory within its heap. Standard `malloc()` calls reach into the kernel via syscalls like `mmap` or `brk`.

### Common Allocators
- **ptmalloc2 (glibc standard)**: The default Linux allocator. Uses **Arenas** to reduce lock contention in multi-threaded programs. High `MALLOC_ARENA_MAX` values can lead to severe memory bloating in 64-bit systems.
- **tcmalloc (Google)**: Thread-Caching malloc. Designed for high concurrency with minimal lock contention by giving each thread its own small cache.
- **jemalloc (Jason Evans / Facebook)**: Highly efficient allocator used in FreeBSD, Firefox, and Rust. Excels at reducing fragmentation (often achieving 20%+ higher efficiency than standard Windows allocators).
- **Go Allocator**: A custom implementation inspired by tcmalloc, dividing memory into pages (8KB) and specific bins (Tiny, Small, Large) to optimize for the language's specific allocation patterns.

---

## Garbage Collection (GC)

Garbage collectors are user-land allocators that automate memory deallocation, trading CPU cycles for developer convenience.

### The Weak Generational Hypothesis
Most objects die young. Modern GCs organize memory into **Generations**:
- **Young Generation (Eden/Survivor)**: Objects are created here. Minor GCs happen frequently.
- **Old Generation (Tenured)**: Long-lived objects promoted from the Young generation. Major GCs happen less often.
- **Permanent/System Space**: For internal metadata and classes that rarely change.

### GC Strategies
1.  **Reference Counting** (Python, Objective-C/Swift): See [[Compiler_Design#Automatic Reference Counting (ARC)|ARC]] for the compiler-side variant.
    - Tracks how many references point to an object. Deletes when count hits zero.
    - **Pros**: Immediate deallocation. 
    - **Cons**: Overhead of counting; cannot handle **Reference Cycles** (A points to B, B points to A) without **Weak/Unowned** references.
2.  **Mark and Sweep** (JVM, Ruby, JavaScript):
    - **Mark**: Starts from roots (stacks, globals) and traverses the object tree, marking reachable objects.
    - **Sweep**: Scans the heap and releases unmarked objects.
    - **Stop the World**: Historically required pausing the entire application to ensure memory consistency during the scan.

### Performance and Compaction
- **Compact Copying Collector** (JVM, Erlang): Moves active objects to a new contiguous memory area. This eliminates **Internal Fragmentation** but requires the runtime to handle references instead of raw pointers (since physical addresses change).
- **Tri-color Marking**: (White, Gray, Black) algorithm used for **Concurrent/Incremental GC** to minimize "Stop the World" pauses by marking objects while the application is still running.

### Optimization Note: `MALLOC_ARENA_MAX`
In memory-constrained Linux environments ([[Virtualization_and_High_Performance_Systems|containers]], small VPS), setting `MALLOC_ARENA_MAX=2` can prevent the glibc allocator from creating too many arenas, significantly reducing memory waste at a minor cost to peak [[Concurrency_and_Parallelism|multi-threaded]] performance.
