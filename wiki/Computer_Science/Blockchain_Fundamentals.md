---
tags: [architecture, databases, blockchain]
date_created: 2026-04-12
sources: 
  - "[[Blockchains servem pra Eleições？]]"
---
# Blockchain Fundamentals

A Blockchain is effectively an append-only distributed database (digital ledger) prioritizing immutability and absolute consensus over raw performance, similar to how [[Database_Fundamentals|NoSQL]] prioritized scale over consistency (CAP Theorem limits). Its core data structure is a [[Merkle_Trees_and_DAGs|Merkle Tree]].

## Non-Fungibility and Consensus
The definitive innovation of protocols like Bitcoin wasn't just digital money, but the concept of digital **non-fungibility**. Through Byzantine fault tolerance methods (like Proof of Work), chains guarantee that a digital asset is unique and not infinitely duplicable. See [[Cryptographic_Hashing|Cryptographic Hashing]] and [[BitTorrent_and_Distributed_Networks|BitTorrent]] for related distributed integrity mechanisms.

## Applicability (Why it fails for Public Elections)
While an immutable ledger guarantees data integrity, it fundamentally fails the secrecy requirement of public ballots.
- **Public Tracking**: Blockchains operate on sequential timestamps and traceable addresses. Even if nominally masked, analyzing the first transaction timestamp easily correlates identities (e.g., matching the polling station president's vote).
- **Misplaced Architecture**: Blockchain guarantees a recorded transaction is mathematically permanent. It does *not* guarantee the transaction wasn't fraudulently inserted originally by [[Malware_and_Ransomware_Defenses|malware]] on the voting terminal. Replacing paper trails with blockchains for secret elections represents a fundamental misunderstanding of the technology's threat model.
