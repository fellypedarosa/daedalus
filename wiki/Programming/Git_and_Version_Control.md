---
tags: [git, software_engineering, tooling, workflow]
date_created: 2026-04-12
sources:
  - "[[Akitando 71 - Usando Git Direito]] (Clipper)"
---

# Git and Version Control

Git is not just a backup tool; it is a collaborative database of project history. Professional use requires maintaining a high-fidelity, readable record. For the internal data structures (SHA-1, DAGs, Merkle Trees), see [[Git_Algorithms_and_Internals|Git Algorithms and Internals]].

## Commit Philosophy

Commit messages should be precise. Avoid junk messages like "fix", "updated", or "hotfix".

### Atomic Commits
- A commit should contain exactly **one logical change**.
- **The Patch Pattern**: Use `git add -p` (patch/hunk) to split changes in a single file into separate, logical commits.
- **The Interactive Pattern**: Use `git add -i` to manage the stage with surgical precision.

### History Management
- **`git commit --amend`**: Instantly fix the last commit (message or content).
- **`git reset --soft`**: Reverts commits from history while keeping changes in the staging area. Use this to regroup multi-part "fixing" commits into one professional commit before merging.
- **`git rebase -i` (Interactive Rebase)**:
    - **Pick**: Keep the commit.
    - **Squash**: Merge the commit into the previous one (amalgamation).
    - **Reword**: Change the message.

## Safety and Recovery

The **Reflog (`git reflog`)** is the ultimate safety net.
- Even if you `git reset --hard` and lose commits, they are still present in Git’s internal database for a period (marking them for future garbage collection). See [[Local_Git_Resilience|Local Git Resilience]] for backup strategies.
- Use the Reflog to find the SHA-1 of the "lost" state and create a new branch from it.
- **`git gc`**: Manually triggers the garbage collector to purge orphaned objects (the "trash can").

## Managing Large Repositories

### Binary Files and Bloat
Git tracks **content**, not files. For text, it saves deltas. For binaries (PSD, Video, Audio), it saves the **entire file** for every change.
- **Git LFS (Large File Storage)**: Replaces large binaries in the Git tree with small pointer files, storing the massive data in specialized storage. Essential for design-heavy or media-heavy repos.
- **BFG Repo Cleaner**: A high-performance Java tool (Big Fucking Gun) used to purge accidentally committed large files or sensitive data (passwords) from the entire repository history. 
    - *Warning*: This rewrites history (changes all SHA-1s), requiring all collaborators to re-clone.

## Architectural Models

### Monorepo vs. Multirepo
- **Monorepo** (Google, Meta): One giant repository for the entire company. Requires significant custom tooling for scaling but simplifies dependency management and large-scale refactoring.
- **Multirepo**: Individual repositories for each service/module. Minimal overhead but can lead to "Dependency Hell." See [[Linux_Internals_and_FHS#Dynamic Linking|Dynamic Linking]].

### The "Mesh" Model
The **Linux Kernel** development (the origin of Git) uses a **Mesh/Monotree** model:
- Development is distributed across multiple organizations (Canonical, RedHat, independent mantainers).
- Coordination happens via **Mailing Lists and Patches** (`git send-email` / `git am`) rather than a single centralized GitHub Pull Request system.
- This model allows patches to be distributed simultaneously to multiple versions/roots of the kernel without centralized gatekeeping.
