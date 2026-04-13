---
tags: [programming, paradigms, rad, engineering_history]
date_created: 2026-04-12
sources:
  - "[[Akitando 40 - Entendendo Back-End para Iniciantes em Programação (Parte 1) | Série Começando aos 40]] (Clipper)"
  - "[[Akitando 41 - Entendendo Back-End para Iniciantes em Programação (Parte 2) | Série Começando aos 40]] (Clipper)"
---
# Programming Paradigms and History

The way we organize code (paradigms) has evolved from simple hardware instructions to massive componentized enterprise systems.

## RAD and Componentization (1990s)
The 1990s marked the era of **RAD (Rapid Application Development)** and the visual construction of software.
- **Visual Tools**: PowerBuilder, Visual Basic, and Delphi (Object Pascal) allowed developers to "drag and drop" components onto windows.
- **Component Models**:
    - **COM (Component Object Model - Windows)**: A language-independent standard for binary component interaction. Everything followed the `IUnknown` interface.
    - **OCX/ActiveX**: Visual components distributed as `.ocx` files.
    - **DCOM/CORBA**: Distributed component models intended for communication between servers in a network.

## The Enterprise Era: J2EE vs. Modern Agile
As business needs grew, "Enterprise" architectures emerged to handle complex distributed transactions.
- **J2EE (Java 2 Enterprise Edition)**: A monumental specification involving **Servlets**, **EJB (Enterprise Java Beans)**, and heavy use of **XML** for configuration. It favored "3-tier" architectures: Client -> App Server -> Database.
- **The XML Backlash**: The complexity of J2EE (and the SOAP protocol) led to a demand for simpler, "Agile" frameworks.
- **The Rails Impact**: **Ruby on Rails (2004)** introduced a new paradigm focused on developer happiness, convention over configuration, and Agile practices (XP, TDD). It moved the industry from monumental enterprise systems to tech startups and microservices.

## Dependency Management: From Hell to Automation
Reusing code requires managing third-party libraries (dependencies), a historically painful process.
- **DLL Hell (Windows)**: Programs conflicting over different versions of the same shared library (`.dll`).
- **Manual Linking**: Linux developers manually downloading tarballs, running `./configure`, `make`, and `make install`, often running into missing library errors.
- **Modern Package Managers**: 
    - **Maven (Java)**: The first to provide a centralized repository and transitive dependency resolution.
    - **NPM (JavaScript)**: Popularized by Node.js, becoming one of the largest dependency ecosystems.
    - **Bundler (Ruby)**: Introduced the concept of the "Lockfile" to ensure exact versions across all environments.
    - **Go/Rust/Elixir**: Modern languages integrating dependency management directly into the core toolchain (Go Modules, Cargo, Hex).

## Advanced Execution Models
- **Managed Runtimes**: JVM (Java) and CLR (.NET) provide "Write Once, Run Anywhere" via intermediate bytecode and JIT (Just In Time) compilation.
- **Actor Model**: Originating from Lisp/Smalltalk influence, popularized by Erlang for telecom resilience, then adopted by Akka (Scala) and Elixir. It emphasizes state isolation and message passing as a primary paradigm over shared-memory OOP.
