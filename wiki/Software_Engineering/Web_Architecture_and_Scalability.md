---
tags: [software_engineering, architecture, scalability, web]
date_created: 2026-04-12
sources:
  - "[[Akitando 112 - Subindo Aplicações Web em Produção]] (Clipper)"
  - "[[Akitando 113 - A Forma Ideal de Projetos Web]] (Clipper)"
  - "[[Akitando 140 Desbloqueando o Algoritmo do Twitter - Introdução a Grafos]] (Clipper)"
  - "[[Akitando 142 - Entendendo COMO ChatGPT Funciona - Rodando sua Própria IA]] (Clipper)"
---
# Web Architecture and Scalability

Modern web development moves beyond the "tutorial" stage—where everything runs on a single server—to distributed systems designed for reliability and massive throughput.

## Core Infrastructure

### 1. Reverse Proxy (NGINX)
No modern web process (Node, Rails, Django) should be exposed directly to the internet.
- **Roles**: [[TLS_and_Certificate_Authorities|SSL/TLS]] Termination, Load Balancing (Round Robin), and serving static assets. See [[Firewalls_and_Proxies|Firewalls and Proxies]].
- **Safety**: Buffers slow clients and heavy uploads, protecting the application process from saturation.

### 2. 12-Factor App Methodology
A set of best practices for building scalable SaaS applications:
- **Statelessness**: Processes are ephemeral. No data is stored on the local disk (use S3 or DB).
- **External Config**: Store secrets and settings in Environment Variables (`ENV`).
- **Backing Services**: Treat databases, queues, and caches as attached resources.

## Performance Optimization

### The Throughput Equation
*Capacity = (Total Processes &times; Frequency) / Avg Response Time*.
To scale, you must either increase processes (**Horizontal Scaling**) or decrease response time (**Optimization**).

### Caching (The 10x Win)
Using in-memory stores like **Redis** or **Memcached** to store expensive query results. See [[Database_Fundamentals#Hybrid Architecture|Polyglot Persistence]] for caching strategy.
- **Impact**: A homepage query that takes 100ms on a DB can take <1ms in cache.
- **Strategy**: Cache frequently accessed, slow-changing data (lists, profiles).

### Database Scaling
- **Connection Pooling**: DB connections are finite. Use pools (managed by libraries or tools like **pgbouncer**) to reuse connections. See [[PostgreSQL]] and [[Concurrency_and_Parallelism|Concurrency]].
- **Read/Write Split**: Direct all writes to a Primary DB and scale reads through multiple **Read Replicas**.
- **Query Optimization**: SQL indices and efficient joins are more impactful than language changes.

## Asynchronous Processing (Queues)

Never make a user wait for a slow external process (Email, Payments, Image Processing).
- **Mechanism**: The web process pushes a "Job" to a queue (Redis, Kafka, SQS) and returns `200 OK` immediately.
- **Workers**: Separate background processes pick up jobs from the queue and execute them.
- **Control**: Allows for graceful retries, backoff strategies, and independent scaling of "heavy" tasks. See [[Deployment_Workflows|Deployment Workflows]].

## High-Scale Systems Case Study: Twitter

Scaling to hundreds of millions of users requires a shift from monolithic applications to specialized internal services.

### 1. The Migration to Scala/JVM
Twitter famously migrated its core architecture from Ruby on Rails to **Scala** and the **JVM**.
- **Concurrency**: The JVM's mature threading and the actor model in Scala (via **Finagle**) allowed handling massive request volumes that were bottlenecking the single-threaded Ruby GIL.
- **Type Safety**: Functional programming features in Scala reduced bugs in complex distributed systems while maintaining developer productivity.

### 2. Specialized Infrastructure Services
To handle petabytes of data, Twitter developed (and often open-sourced) specific services:
- **Snowflake**: A service for generating unique, roughly time-ordered IDs at scale.
- **Thrift/Protobuf**: Binary serialization protocols that are much faster and more compact than JSON for service-to-service communication.
- **Gizzard/FlockDB**: Frameworks for distributed data storage and querying social graphs.
- **Earlybird**: A real-time search engine based on Lucene.

### 3. Production vs. Tutorial Code
The primary difference in high-scale systems is the handling of **failure modes**:
- **Tutorial Code**: Assumes connections never drop, resources are infinite, and logic is synchronous.
- **Production Code**: Implements circuit breakers, retries with exponential backoff, timeouts, and rate limiting to prevent "cascading failures" in distributed environments.
