---
tags: [databases, sql, nosql, architecture, acid, scaling]
date_created: 2026-04-12
sources:
  - "[[Akitando 49 - Devo usar NOSQL | ENDGAME para Iniciantes em Programação]] (Clipper)"
---

# Database Fundamentals

The choice of database architecture is a fundamental trade-off between consistency, durability, and scalability. There is no "silver bullet."

## Relational Databases (RDBMS)

Relational databases like **[[PostgreSQL]]** and **MySQL/MariaDB** are the standard for most applications, offering strong consistency and relational modeling.

### Underlying Structures: B-Trees vs LSM Trees
- **B-Trees (Clustered Indexes)**: Traditional RDBMS engines store data using B-Trees, allowing efficient (O(log n)) reads and range queries. However, they suffer under heavy random writes because updating the tree structure requires modifying specific disk pages, causing fragmentation overhead. Related: [[Storage_and_Filesystems#Modern Filesystems|Filesystem B+Trees (NTFS)]].
- **LSM Trees (Log-Structured Merge-Trees)**: Used commonly in write-heavy NoSQL databases (e.g., Cassandra). LSM Trees batch writes into memory first (MemTable) and then flush them sequentially to immutable disk segments (SSTables), providing immense write throughput at the cost of slightly slower, more complex reads requiring Bloom Filters to locate data rapidly. See also [[Cryptographic_Hashing|Hashing]] for Bloom Filter internals.

### Key Characteristics
- **ACID Guarantees**:
    - **Atomicity**: All-or-nothing transactions.
    - **Consistency**: Data remains in a valid state (rules, triggers, constraints).
    - **Isolation**: Concurrent transactions don't interfere.
    - **Durability**: Committed data survives system crashes.
- **MVCC (Multi-version Concurrency Control)**: Allows multiple connections to write and read without blocking each other by maintaining multiple "versions" of a row. Related: [[Concurrency_and_Parallelism|Concurrency and Parallelism]].
- **Scaling Complexity**: Scaling writes in RDBMS is difficult due to ACID overhead. Common strategies involve Read Replicas (scaling reads) and **Sharding** (partitioning data horizontally), though sharding adds massive architectural complexity.

## NoSQL Databases

NoSQL emerged to solve specific scaling and schema flexibility problems, often by relaxing consistency.

### Types and Sweet Spots
- **Document Stores (MongoDB)**: Data as JSON/BSON. 
    - *Sweet spot*: Dataset fits in RAM; schema flexibility.
    - *Trade-off*: Relaxed durability (by default, it acknowledges writes before disk flush).
- **Wide Column / Distributed (Cassandra)**:
    - *Sweet spot*: Massive write throughput across multiple regions.
    - *Constraint*: No Joins; queries must be pre-planned and indexed.
- **Key-Value Stores (Redis)**: 
    - *Sweet spot*: High-speed cache, counters, session management.
    - *Usage*: Often used as a buffer/cache in front of an RDBMS.

## In-Practice Strategies

### Pragmatic Denormalization
While "Third Normal Form" (3NF) is academically elegant, it often kills performance due to expensive **Joins**. 
- **Strategy**: Duplicate data (e.g., storing a state name directly in a user profile) to avoid joins on data that rarely changes.
- **Cost**: Consistency management moves from the database level to the application code.

### Scaling Writes with Queues
To handle massive spikes (e.g., Black Friday), applications should avoid direct RDBMS writes.
1.  **Queue Implementation**: Use a message broker (RabbitMQ, SQS, Redis Pub/Sub).
2.  **Worker Pattern**: Application puts "Write Intent" into the queue.
3.  **Background Processing**: Dedicated workers consume the queue and write to the database at a controlled pace, preventing the DB from being overwhelmed by concurrent connections. See [[Web_Architecture_and_Scalability|Web Architecture and Scalability]].

### Hybrid Architecture
Most high-performance applications use a **Polyglot Persistence** model:
- **RDBMS**: Source of truth for transactional/sensitive data (Users, Billing).
- **Redis/Memcached**: For performance-critical reads and transient state.
- **Elasticsearch**: Specialized for Full-Text Search and relevancy (faster than RDBMS regex/like queries).

## Administrative Recommendation
"The database is the most difficult part of the infrastructure to maintain."
- Use **Managed Services** (AWS RDS/Aurora, Google Cloud SQL) whenever possible to delegate backups, patching, and failover management. See [[Deployment_Workflows|Deployment Workflows]].
- Use **CDN/WAF** (Cloudflare) on the front line to filter malicious traffic and prevent DDoS attacks on the application and database layers.
