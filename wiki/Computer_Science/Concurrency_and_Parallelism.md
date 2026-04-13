---
tags: [computer_science, concurrency, parallelism, systems_design]
date_created: 2026-04-12
sources:
  - "[[Akitando 43 - Concorrência e Paralelismo (Parte 1) | Entendendo Back-End para Iniciantes (Parte 3)]] (Clipper)"
  - "[[Akitando 44 - Concorrência e Paralelismo (Parte 2) | Entendendo Back-end para Iniciantes (Parte 4)]] (Clipper)"
---
# Concurrency and Parallelism

High-fidelity understanding of non-sequential execution and the coordination of computational units.

## Core Definitions
- **Concurrency**: Dealing with multiple tasks at once. It is a property of the program structure. Tasks can be interleaved via context switching (time-sharing) without necessarily running at the exact same physical instant.
- **Parallelism**: Executing multiple tasks at once. It is a property of the physical hardware (Multi-core CPUs, GPUs). See [[Hardware_Architecture|Hardware Architecture]].
- **Theorem**: All parallelism implies concurrency, but not all concurrency implies parallelism.

## Coordination and Synchronization
The primary challenge of concurrent programming is coordinating access to shared resources (Memory, I/O, Files).

### Primitives
- **Mutex (Mutual Exclusion)**: A "Lock" that ensures only one execution unit (thread/process) can access a resource at a time.
- **Race Condition**: A bug where the system's output is non-deterministic because multiple units are racing to modify shared data simultaneously.
- **Deadlock**: A stalemate where two units are waiting for each other to release locks (Resource A waits for B, B waits for A).

### Performance Costs
- **Context Switching**: The [[Operating_System_Internals|OS Kernel]] saving the registers/state of one thread and loading another. This incurs overhead in CPU cycles and memory.
- **Syscall Boundaries**: Jumping between **User Land** (Ring 3) and **Kernel Space** (Ring 0) to manage threads or I/O is expensive.

## The C10K Problem (1999)
Coined by Dan Kegel, it describes the challenge of handling 10,000 simultaneous connections.
- **Constraint**: Each native thread in an OS typically consumes ~1MB of Stack RAM. 10,000 threads = 10GB RAM, leading to [[Memory_Management|memory exhaustion]] and $O(n)$ scheduling degredation.

## Concurrency Models

### 1. Reactor Pattern (Event Loop)
Used by **NGINX**, **Node.js**, or Python's **Twisted**. See [[Web_Architecture_and_Scalability|Web Architecture]] for NGINX as a reverse proxy.
- **Mechanics**: A single-threaded loop (Reactor) that registers I/O operations with the kernel using non-blocking primitives (`epoll`, `kqueue`). 
- **Efficiency**: No context switching between threads.
- **Trade-off**: Long computational tasks block the entire loop (Head-of-line blocking).

### 2. Actor Model (Message Passing)
Used by **Erlang**, **Elixir**, and **Akka (Scala)**. The BEAM VM on which Erlang runs uses a [[Compiler_Design#Just-in-Time (JIT)|JIT compiler]].
- **Isolation**: Each "Actor" is a lightweight process (green thread) with its own isolated memory (no shared state).
- **Communication**: Done via asynchronous message passing (mailboxes).
- **Supervisors**: A hierarchical "fail fast" strategy where supervisors monitor actors and restart them upon failure.
- **Scaling**: 10,000 Erlang "processes" consume only ~20MB of RAM.

### 3. CSP (Communicating Sequential Processes)
Used by **Go** (Goroutines).
- **Channels**: Goroutines communicate via typed channels (similar to Named Pipes).
- **Shared Memory**: Unlike Erlang, Go allows passing pointers through channels, necessitating manual synchronization (mutexes) if memory is shared.
- **Scheduler**: Go uses a M:N cooperative scheduler in user-land to map thousands of goroutines to a few native kernel threads. See [[Programming_Languages_Ecosystem|Programming Languages]] for Go's design philosophy.

## User-land abstractions
- **Fibers / Coroutines / Generators**: Primitives for cooperative multitasking using `yield` and `resume`.
- **Promises / Futures**: Placeholders for values that will be resolved in the future, often used in Reactor-based environments to avoid "Callback Hell."
- **Green Threads**: Threads managed by a language runtime rather than the OS kernel. They are "lighter" (KB vs MB) and faster to create.
