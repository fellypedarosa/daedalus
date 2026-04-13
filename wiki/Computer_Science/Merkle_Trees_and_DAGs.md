---
tags: [data_structures, cryptography, git]
date_created: 2026-04-12
sources: 
  - "[[Criptografia na Prática - Certificados, BitTorrent, Git, Bitcoin]] (YouTube)"
  - "[[Akitando 147 - Criptografia na Prática - Certificados, BitTorrent, Git, Bitcoin]] (Clipper)"
---
# Merkle Trees and DAGs

A Merkle Tree is a binary tree data structure where leaf nodes are [[Cryptographic_Hashing|cryptographic hashes]] of data blocks, and non-leaf nodes are hashes of their children's concatenation. It ensures deterministic integrity validation algorithmically scaling to massive datasets (like [[Storage_and_Filesystems|ZFS]] pools, [[BitTorrent_and_Distributed_Networks|BitTorrent]] swarms, or [[Git_Algorithms_and_Internals|Git]] graphs) without requiring complete data recalculation.

## Hierarchical Hashing and the Merkle Root
- **Chunk Hashing**: A large file is fragmented into atomic blocks (e.g. 2MB chunks). Each chunk is individually processed into a base hash (like SHA-1).
- **Pairing**: Adjacent chunk hashes are concatenated and re-hashed, repeatedly forming upper layers until converging into a single master cryptographic string known as the **Merkle Root**.
- **Proof of Inclusion**: To verify a specific downloaded chunk's fidelity, a client does not need the entire file. By requesting only the directly adjacent sibling hashes traversing up the tree (`log2(N)` nodes), they can dynamically compute the current trajectory and compare the final output directly against the trusted Merkle Root.

## Git as a Merkle DAG
Git relies on Directed Acyclic Graphs (DAGs) built heavily upon Merkle mechanisms. Every Git commit computes its SHA-1 hash by incorporating the metadata, tree changes, AND the exact SHA-1 pointer of its parent commit.
- **Immutable History**: Modifying a historical commit inevitably alters its hash. This definitively orphans all subsequent child commits because their pre-computed lineage pointers no longer resolve correctly. To "rewrite history" (e.g. via `git rebase`), an orchestrator must forcefully reconstruct every downstream node linearly, generating entirely new commits to restabilize the graph. This mathematical chain is identical to the mechanism securing Blocks in a generic [[Blockchain_Fundamentals|Blockchain]].
