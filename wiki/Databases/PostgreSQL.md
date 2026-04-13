---
tags: [databases, postgresql, indexing, performance]
date_created: 2026-04-12
sources:
  - "[[Akitando 149 - Configurando Docker Compose, Postgres, com Testes de Carga - Parte Final da Rinha de Backend]] (Clipper)"
---
# PostgreSQL: Internals and Optimization

PostgreSQL is a robust, object-relational database system that balances ACID compliance with high-performance extensible indexing.

## Advanced Indexing Mechanisms

PostgreSQL supports several index types beyond standard B-Trees. For complex search scenarios (e.g., Full Text Search or JSONB), generalized indices are required.

### GIST vs GIN
- **GIN (Generalized Inverted Index)**:
    - **Usage**: Optimal for data types with multiple keys (arrays, JSONB, hstore).
    - **Mechanism**: Extracts keys from values and creates an ordered list of pointers to the indexed lines.
    - **Trade-off**: Fast lookups for multi-key queries, but slower to update/insert since every key must be indexed.
- **GIST (Generalized Search Tree)**:
    - **Usage**: A general-purpose indexing technique for spatial data, custom types, and fuzzy text matching.
    - **Mechanism**: Hierarchical tree-based indexing.
    - **Trade-off**: Slower than GIN for pure multi-key searches but significantly faster for updates and "nearest neighbor" lookups.

### Full Text Search (FTS) and Trigrams
Standard SQL `LIKE '%term%'` queries are slow because the leading wildcard necessitates a **Sequential Scan** (checking every row).
- **`pg_trgm` Extension**: Breaks text into "trigrams" (sets of 3 characters).
- **Trigram Indexing**: Using GIST with `gist_trgm_ops` allows PostgreSQL to utilize indices even for partial word matches and wildcards, dropping query times from tens of milliseconds to mere microseconds on small-to-medium datasets.

## Performance Profiling: EXPLAIN ANALYZE

To identify bottlenecks, use the `EXPLAIN ANALYZE` command to see the query plan and execution times.
- **Sequential Scan (Seq Scan)**: The "last resort." The database reads the entire table from disk.
- **Index Scan**: The database uses an index to jump directly to the required data.
- **Bitmap Index Scan / Bitmap Heap Scan**: A hybrid approach where an index identifies candidate rows (bitmap index scan), and then the actual rows are retrieved and filtered from the table (bitmap heap scan).

## Resource Management

### Connection Pooling
Every connection to PostgreSQL creates a new backend process, consuming **2-4 MB of RAM** per connection.
- **Overhead**: 1,000 connections could consume 4 GB of RAM purely on connection management, regardless of the queries being run.
- **Pool Recycling**: Use connection pools (e.g., `PgBouncer` or application-level pools like Node's `pg.Pool`) to keep a stable number of connections (e.g., 20-50) and recycle them between incoming requests.
- **Sizing**: Don't guess the pool size. Monitor the peak active connections using tools like **pgAdmin** or `pg_stat_activity` to find the saturation point.

### Transactions and ROLLBACKs
Every operation inside a transaction that fails (e.g., an `INSERT` that violates a `UNIQUE` constraint) triggers a **ROLLBACK**. In high-stress load tests, a high volume of rollbacks can indicate lock contention or logic errors that waste database cycles.

## Relational JSON: The JSONB Type
While NoSQL databases popularized JSON storage, PostgreSQL's `JSONB` (Binary JSON) allows for structured storage with indexing support. It combines the flexibility of document stores with the strictness of relational integrity.

## Monitoring and Visual Tools
- **pgAdmin**: A comprehensive web-based administration tool for visualizing transaction rates, connection counts, and database health.
- **`pg_stat_statements`**: An extension for tracking execution statistics of all SQL statements executed on the server.
