---
tags: [software_engineering, architecture, scalability, web]
date_created: 2026-04-12
sources:
  - "[[Akitando 112 - Subindo Aplicações Web em Produção]] (Clipper)"
  - "[[Akitando 113 - A Forma Ideal de Projetos Web]] (Clipper)"
  - "[[Akitando 133 - Tornando sua App Web Mais Rápida!]] (Clipper)"
  - "[[Akitando 135 - ChatGPT Consegue te Substituir]] (Clipper)"
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

## Content Delivery Networks (CDN)
Offload static assets (JS, CSS, Images) to global edge servers (CloudFront, Fastly).
- **Impact**: Decreases latency for global users and removes asset requests from the application's infrastructure.
