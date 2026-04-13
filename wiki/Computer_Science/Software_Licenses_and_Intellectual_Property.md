---
tags: [software_engineering, legal, licensing]
date_created: 2026-04-12
sources:
  - "[[Akitando 7 - A Controvérsia da Lerna vs ICE]] (Clipper)"
  - "[[Akitando 73 - RANT A Realidade do Software Livre]] (Clipper)"
  - "[[Akitando 74 - Emacs vs Java]] (Clipper)"
---
# Software Licenses and Intellectual Property

## Philosophical Foundations

The software industry is governed by two major, often conflicting, philosophies regarding freedom:

### Free Software (Libre)
Championed by **Richard Stallman** and the **Free Software Foundation (FSF)**.
- **Focus**: Protecting the user's freedom and the software itself.
- **The Four Freedoms**:
    - **Freedom 0**: To run the program for any purpose.
    - **Freedom 1**: To study how the program works (requires source code) and change it.
    - **Freedom 2**: To redistribute copies to help others.
    - **Freedom 3**: To distribute copies of modified versions.
- **Restrictive/Copyleft**: Uses the **GPL (General Public License)** to ensure that any derivative work remains free. It "restricts" the developer's freedom to close the code in order to "protect" the software's freedom. See [[Compiler_Design#Language Evolution and Licensing|GPL vs LLVM]] for a practical case.

### Open Source
Championed by **Eric Raymond** (author of *The Cathedral and the Bazaar*) and the **Open Source Initiative (OSI)**.
- **Focus**: Pragmatic development methodology, efficiency, and industry adoption. "Given enough eyeballs, all bugs are shallow" (Linus's Law).
- **The Apolitical Mandate (Clause 5)**: According to the OSI definition, a license must not discriminate against any person or group of persons. Open source is designed to be purely technical and amoral. Attempting to restrict usage based on political or ethical disagreements (e.g., the Lerna vs ICE controversy) fundamentally violates the Open Source definition.
- **Permissive Licenses**: (MIT, BSD, Apache) Allow maximum freedom for developers and companies to modify, close, and commercialize the software without releasing source code.
- **Value**: Facilitates corporate collaboration and "Commoditization of the Complement" (sharing costs of non-critical infrastructure). See [[Open_Source_and_Industry_Dynamics|Open Source and Industry Dynamics]].


---

## The Origin of Copyleft

The **GPL** was born out of a conflict between two computing giants: **Richard Stallman** and **James Gosling** (creator of Java).

1.  **Gosling Emacs (GosMacs)**: The first C-based Emacs, distributed freely in the early 80s in a hacker spirit of cooperation.
2.  **Commercialization**: Gosling sold the rights to GosMacs to a company called **UniPress**.
3.  **Conflict**: Stallman had used GosMacs as the foundation for **GNU Emacs**. UniPress/Gosling attempted to restrict Stallman's distribution.
4.  **Reaction**: Stallman spent a week re-writing the remaining Gosling code to excise it from GNU Emacs.
5.  **Legacy**: This event highlighted that "hacker trust" was insufficient. The **GPL** was created to legally enforce the "perpetual freedom" of code, preventing any contributor from unilaterally closing the work of the community.

---

## Critical Licensing Concepts

### Permissive vs. Restrictive (Viral)
- **Permissive (MIT/BSD)**: "Do whatever you want, just include the copyright." Ideal for libraries and frameworks (React, VS Code, Go).
- **Restrictive (GPL)**: "If you use this, your whole project must be GPL." Often called "viral" because it propagates to all derivative works.
- **LGPL (Lesser GPL)**: A compromise allowing proprietary programs to link to a library without being "contaminated," provided the library itself remains free.

### The SaaS Loophole and AGPL
The standard GPL only triggers the requirement to release source code upon **distribution** (giving someone a binary).
- **The Loophole**: Cloud providers (SaaS) "use" the software on their servers but never "distribute" it to the user (they only provide an API).
- **AGPL (Affero GPL)**: Created to close this loophole. It requires source code disclosure if the software is used over a network (SaaS). Big Tech companies (Google, AWS) typically ban AGPL internally to protect their proprietary backends.

### Tivoization and GPLv3
Named after **TiVo**, which used Linux (GPLv2) but used digital signatures in hardware to prevent users from running modified versions of that code.
- **GPLv3**: Specifically designed to prohibit Tivoization by requiring the disclosure of "Installation Information" (keys/signatures) needed to run modified software on the hardware.

---

## Legal Landmarks

### Oracle vs. Google (The Java Trap)
- **Context**: Google implemented the Android APIs using **Apache Harmony** (a clean-room implementation of Java), but it included 11,500 lines of original Java API code.
- **The Conflict**: Oracle bought Sun (owners of Java) and sued Google for copyright infringement.
- **The Question**: Can an **API** (Application Programming Interface)—the "names" of the functions—be copyrighted?
- **Implications**: If APIs are copyrightable, industry standards like **POSIX** (implemented by Linux) could be used by owners (Micro Focus) to claim rights over open-source operating systems.

### POSIX and Linux
Linux is a "Free Software" implementation of the **POSIX** standard (originally from UNIX). This standard defines how a system should behave. See [[Operating_Systems_History|Operating Systems History]] and [[Linux_Internals_and_FHS|Linux Internals]]. The legal battle over API copyright directly threatens the "clean-room" implementation model that allowed Linux to flourish as a replacement for proprietary UNIX systems.

---

## Metadata
- **Source**: LNK [Akitando #7](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%207%20-%20A%20Controv%C3%A9rsia%20da%20Lerna%20vs%20ICE.md), [Akitando #73](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%2073%20-%20RANT%20A%20Realidade%20do%20Software%20Livre.md), [Akitando #74](file:///home/rosa/Dropbox/Daedalus/raw/clipper/Akitando%2074%20-%20Emacs%20vs%20Java.md)
- **Status**: #ingested
