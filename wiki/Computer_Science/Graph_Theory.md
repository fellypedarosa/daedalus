---
tags: [computer_science, algorithms, math, networking]
date_created: 2026-04-16
sources:
  - "[[Akitando 140 Desbloqueando o Algoritmo do Twitter - Introdução a Grafos]] (Clipper)"
---
# Graph Theory

Graph Theory is the study of mathematical structures used to model pairwise relations between objects. In computer science, it is the foundation for social networks, recommendation engines, and distributed system topology.

## Core Concepts

### 1. Components
- **Nodes (Vertices)**: The individual entities in the system (e.g., Users, Web pages).
- **Edges (Links)**: The relationships between entities (e.g., Follows, Likes, Hyperlinks).
  - **Directed**: Edges have a direction (User A follows User B).
  - **Undirected**: Relationships are mutual (User A is friends with User B).
  - **Weighted**: Edges have a value representing strength or distance.

### 2. Graph Structures
- **Connected Graph**: There is a path between every pair of vertices.
- **DAG (Directed Acyclic Graph)**: A directed graph with no cycles. Critical for Git internals, build systems, and task scheduling.
- **Social Graph**: A representation of social relationships, often mapped using large-scale distributed databases.

## Algorithms and Scoring

### 1. Centrality and Influence
Determining which nodes are the most "important" in a network:
- **Degree Centrality**: Based simply on the number of edges connected to a node.
- **Hubs and Authorities (HITS)**: Proposed by Jon Kleinberg. 
  - **Authorities**: Nodes that contain valuable information (pointed to by many hubs).
  - **Hubs**: Nodes that point to many high-quality authorities.

### 2. Recommendation Engines
- **PageRank**: The original Google algorithm. It assigns a numerical weighting to each element of a hyperlinked set of documents, based on the principle that more important websites likely receive more links from other websites.
- **SALSA (Stochastic Approach for Link-Structure Analysis)**: A variation of HITS used by **Twitter** for its "Who to Follow" recommendations. It uses a random walk on a bipartite graph (Users and their Interests/Follows) to identify relevant suggestions.
- **GraphJet**: Twitter's real-time graph processing engine that maintains a massive in-memory social graph to provide low-latency recommendations.

## Real-world Applications
- **Pathfinding**: Finding the shortest route in a map (Dijkstra's Algorithm).
- **Network Topology**: Mapping the structure of the internet or local networks.
- **Fraud Detection**: Identifying suspicious clusters of transactions or accounts.

## See Also
- [[Theoretical_Computer_Science]]
- [[Web_Architecture_and_Scalability]]
