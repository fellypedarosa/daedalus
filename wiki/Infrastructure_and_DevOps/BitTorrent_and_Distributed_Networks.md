---
tags: [networking, protocols, decentralization]
date_created: 2026-04-12
sources: 
  - "[[Criptografia na Prática - Certificados, BitTorrent, Git, Bitcoin]] (YouTube)"
  - "[[Akitando 147 - Criptografia na Prática - Certificados, BitTorrent, Git, Bitcoin]] (Clipper)"
---
# BitTorrent and Distributed Networks

BitTorrent mitigates the central point of failure plaguing standard HTTP servers by distributing a file as cryptographic chunks across an ephemeral swarm of user-operated endpoints (peers). 

## Trackers, DHT, and PEX
- **Trackers**: Originally, BitTorrent relied on centralized HTTP/UDP signaling endpoints (Trackers) that maintain temporal IP rosters of connected peers seeking specific InfoHashes.
- **DHT and Peer Exchange (PEX)**: Modern implementations implement decentralization by shifting network orchestration directly onto the peers. Using Distributed Hash Tables (DHT), each swarm participant serves as a miniature router, mapping out proximity nodes via a 160-bit ID space algorithm loosely resembling NoSQL clusters (like Dynamo or Cassandra). This mathematically guarantees peer discovery even if all central tracker servers are eradicated.

## InfoHashes and Magnet Links
The core anchor of a BitTorrent swarm is the **InfoHash**—the deterministic cryptographic fingerprint of the target file's metadata and chunk map. Magnet Links (`magnet:?xt=urn:btih:<hash>`) strictly encode this InfoHash using URIs. When executed, a client queries the DHT matrix for any node broadcasting availability for that precise hash signature, dynamically initiating P2P handshakes.
