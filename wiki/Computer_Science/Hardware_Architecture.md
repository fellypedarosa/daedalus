---
tags: [computer_science, hardware, cpu, arch, arm, x86]
date_created: 2026-04-12
sources:
  - "[[Akitando 87 Turing Complete, Emuladores e o Chip ARM M1]] (Clipper)"
  - "[[Akitando 42 - Apple, GPL e Compiladores]] (Clipper)"
---
# Hardware Architecture

The physical design of a CPU determines its efficiency, power consumption, and the complexity of the software required to run it.

## CISC vs. RISC

### CISC (Complex Instruction Set Computing)
- **Philosophy**: Minimize the number of instructions per program by having single instructions that perform complex tasks (e.g., "draw a window").
- **Example**: **x86** (Intel, AMD).
- **Instruction Length**: Variable (1 to 15 bytes in x86).
- **Cons**: Variable length makes it extremely difficult for the CPU to "predict" and parallelize the decoding of instructions, limiting the **pipeline width**.

### RISC (Reduced Instruction Set Computing)
- **Philosophy**: Use simple, atomic instructions (e.g., "draw a line"). Complex tasks are built by the [[Compiler_Design|compiler]] using sequences of these simple steps.
- **Example**: **ARM**, **M1**, **PowerPC**, **RISC-V**.
- **Instruction Length**: Fixed (usually 2 or 4 bytes).
- **Pros**: Fixed lengths allow for predictable decoding, enabling much wider pipelines and higher performance per clock (IPC).

## CPU Internals and Performance

### Pipelining and Decoding
- **Pipeline Width**: The number of instructions a CPU can decode and execute in a single clock cycle.
- **x86 Limit**: Due to variable instruction length, x86 CPUs typically decode **4 instructions/cycle**.
- **ARM M1**: Since instructions are fixed length, the M1 can decode **8 instructions/cycle**. This allows a 2GHz ARM chip to potentially outperform a 3GHz x86 chip.

### Register Pressure
Registers are the "on-chip" [[Memory_Management|memory]] slots used as arguments for instructions.
- **x86-64**: Has **16** general-purpose registers.
- **ARMv8 (64-bit)**: Has **32** general-purpose registers.
- **Emulation Advantage**: It is easier for an ARM chip to emulated x86 because it has "spare" registers to map the target architecture's state. When x86 tries to emulated ARM, it runs out of registers and must "spill" data to slow RAM, degrading performance significantly.

## Case Study: Apple M1 (Silicion Transition)

The success of Apple's M1 chip was driven by three technical pillars:
1. **Vertical Integration**: Designing the silicon specifically for the OS/[[Compiler_Design|Compiler]] (Clang).
2. **Unified Memory Architecture (UMA)**: High-bandwidth, low-latency memory shared between CPU and GPU, eliminating data copying overhead.
3. **[[Compiler_Design#Emulation and Binary Translation|Rosetta 2]]**: A high-performance translation layer. It benefits from **TSO (Total Store Ordering)** hardware support in the M1, which mimics x86's memory consistency model, allowing emulated code to run at near-native speeds.

## Simulators vs. Emulators

- **Simulator**: Compiles the *source code* for the local architecture. 
    - *Example*: iOS Simulators on a Mac compile the app for x86 (or ARM Mac) instead of the actual iPhone binary.
- **Emulator**: Translates the *binary instructions* of one architecture (e.g., ARM) to another (x86) at runtime. See [[Emulation_on_Linux|Emulation on Linux]].
    - *Example*: Android Emulators using [[Virtualization_and_High_Performance_Systems|QEMU]] often run much slower because every instruction needs translation.
