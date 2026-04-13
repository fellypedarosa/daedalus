---
tags: [computer_science, theoretical_cs, logic, math]
date_created: 2026-04-12
sources:
  - "[[Akitando 87 Turing Complete, Emuladores e o Chip ARM M1]] (Clipper)"
---
# Theoretical Computer Science

Theoretical Computer Science (TCS) deals with the mathematical foundations of computing, focusing on what can be computed and how efficiently.

## Turing Machines

Proposed by **Alan Turing** in 1936, the Turing Machine is a mathematical model of computation. It consists of:
- **Infinite Tape**: Divided into cells, each holding a symbol (0 or 1).
- **Head**: Can read and write symbols on the tape and move left or right.
- **State Register**: Stores the current state of the machine.
- **Action Table**: A set of rules that tells the machine what to do based on the current state and the symbol being read.

### Universal Turing Machine (UTM)
A **Universal Turing Machine** is a Turing Machine that can simulate ANY other Turing Machine. 
- It takes a **Description Number** (the "program") and an input string.
- This is the conceptual basis for the **Stored-Program Computer**: a single piece of hardware that can perform any task by loading different software.

### Turing Completeness
A system (language, CPU, or even a game) is **Turing Complete** if it has the same computational power as a Universal Turing Machine.
- **Criteria**: It must be able to perform conditional branching (if/else) and arbitrary memory access (looping/state).
- **Doom Test**: A common heuristic in tech culture is "Can it run Doom?". If a device (like a pregnancy test or a calculator) can run an emulated Doom, it is almost certainly Turing Complete.

## Limits of Computation

### The Halting Problem
Turing proved that there are problems that **cannot be solved** by any algorithm.
- The **Halting Problem** asks: "Given a program and an input, will it eventually stop or run forever?"
- Turing showed there is no general algorithm that can answer this for all possible program-input pairs.

### Computable vs. Non-Computable Functions
- **Computable**: Functions that can be solved by a Turing Machine in finite time.
- **Non-Computable**: Functions that exist mathematically but cannot be resolved by any universal computer, regardless of time or power (e.g., Godel's Incompleteness related problems).

## Complexity and Emulation

A key takeaway from UTM theory is that **performance != capability**:
- A slow computer (like an 8-bit microcontroller) can simulate a fast computer (like a modern x86 CPU), provided it has enough memory. The only difference is the **time complexity** of the simulation.
- This is why **Emulators** are possible across different instruction sets.
