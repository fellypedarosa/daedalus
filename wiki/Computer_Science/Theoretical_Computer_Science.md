---
tags: [computer_science, theoretical_cs, logic, math]
date_created: 2026-04-12
sources:
  - "[[Akitando 87 Turing Complete, Emuladores e o Chip ARM M1]] (Clipper)"
  - "[[Akitando 140 Desbloqueando o Algoritmo do Twitter - Introdução a Grafos]] (Clipper)"
  - "[[Akitando 142 - Entendendo COMO ChatGPT Funciona - Rodando sua Própria IA]] (Clipper)"
  - "[SUPERINTELIGÊNCIA ARTIFICIAL - Podcast 1583](file:///home/rosa/Dropbox/Daedalus/raw/youtube/cataloged/Podcast_1583_Superinteligencia.md) (Clipper)"
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
- it takes a **Description Number** (the "program") and an input string.
- This is the conceptual basis for the **Stored-Program Computer**: a single piece of hardware that can perform any task by loading different software.

## The Quest for Formalism: Hilbert, Gödel, and Turing

At the turn of the 20th century, mathematicians led by **David Hilbert** sought to formalize all of mathematics into a complete, consistent, and decidable system—a metaphorical "Machine of Truth."

1. **Hilbert's Goal**: To prove that every mathematical statement can be determined to be true or false.
2. **Gödel's Incompleteness Theorems (1931)**: **Kurt Gödel** proved that any consistent mathematical system (capable of basic arithmetic) is necessarily **incomplete**. There will always be true statements that cannot be proven within the system.
3. **The Halting Problem (Turing, 1936)**: **Alan Turing** and **Alonzo Church** showed that mathematics is also **undecidable**. No algorithm can exist that determines the truth/falsehood of all mathematical statements.
    - **Note**: The Universal Turing Machine was originally designed by Turing as a mathematical device to *disprove* Hilbert's decidability, not primarily as a tool for engineering.

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
- **Non-Computable**: Functions that exist mathematically but cannot be resolved by any universal computer, regardless of time or power (e.g., Gödel's Incompleteness related problems).

### Computable Numbers
Turing defined **Computable Numbers** as those whose decimals can be calculated by a Turing Machine (bits).
- **Integers**: Computers excel at discrete integers within a specific range (e.g., 64-bit limits).
- **Floating Point Reality**: Most of the infinite range of real, irrational, and complex numbers are NOT computable. Computers use **approximations** (e.g., IEEE 754), leading to fundamental errors in high-precision math (e.g., $0.1 + 0.2 \neq 0.3$).
- **Paradigm Limit**: No amount of CPU scaling, memory, or speed can bridge the gap between "Digital Integers/Approximations" and the "Mathematical Continuum."

## Mathematics for Computing

The modern explosion of AI/ML and Big Data relies on mathematical branches that go beyond basic logic:

### 1. Linear Algebra (Vector Spaces)
Data in Large Language Models and Recommendation Engines is represented as **Tensors** (multi-dimensional arrays).
- **Embeddings**: Converting words or images into vectors in a high-dimensional space.
- **Cosine Similarity**: A technique to measure the "distance" or similarity between two vectors (e.g., determining if two tweets are related).
- **Matrix Multiplications**: The core operation of GPUs, which are specialized for parallelized linear algebra rather than scalar logic.

### 2. Calculus (Optimization)
Training a neural network is an optimization problem solved using calculus:
- **Loss Functions**: Mathematical functions that quantify the error between a model's prediction and the actual truth.
- **Gradients**: Vectors that point in the direction of the steepest increase/decrease of the loss function.
- **Backpropagation**: An application of the **Chain Rule** to iteratively update the model's parameters (weights) to minimize the loss.
- **Gradient Descent**: The primary algorithm for finding the "global minimum" (optimal state) of a neural network.

### 3. Graph Theory
The study of relationships between objects represented as **Nodes** (vertices) and **Edges**.
- **Social Graphs**: Representing users as nodes and their interactions (follows, likes) as edges.
- **Recommendation Algorithms**: Using graph traversal and scoring (PageRank, HITS) to find influential "Hubs" and "Authorities."
- See [[Graph_Theory]] for deeper technical details.

## Complexity and Emulation

A key takeaway from UTM theory is that **performance != capability**:
- A slow computer (like an 8-bit microcontroller) can simulate a fast computer (like a modern x86 CPU), provided it has enough memory. The only difference is the **time complexity** of the simulation.
- This is why **Emulators** are possible across different instruction sets.
