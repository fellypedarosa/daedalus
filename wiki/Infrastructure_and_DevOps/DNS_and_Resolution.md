---
tags: [networking, web, security]
date_created: 2026-04-12
source: "[[Como sua Internet Funciona ｜ Introdução a Redes Parte 3]]"
---
# DNS and Resolution

The Domain Name System (DNS) is effectively the phonebook of the internet. It translates human-readable URIs (e.g., `youtube.com`) into routable IP Addresses (like `142.250.218.14`).

## Hierarchy and Records
- **A / AAAA Records**: The "final destination" mapping to an IPv4 (A) or IPv6 (AAAA) address.
- **CNAME (Canonical Name)**: An alias. `store.example.com` might point to `shopify.com`, which eventually resolves to an A record.
- **MX Records**: Handles mail routing.
- **TTL (Time to Live)**: The number of seconds a DNS record is cached. Low TTL allows for fast migration; high TTL reduces network noise.

## Architectural Scalability

### Round-Robin
For a single domain like `google.com`, the DNS server might return a list of 10 different IP addresses. The client selects one (often the first), effectively spreading the load across multiple physical data centers.

### Anycast Routing
Sophisticated providers (Cloudflare, Google) use **Anycast**, where multiple servers in different geographic locations share the same IP address. Routers on the internet automatically send your request to the "closest" server (lowest number of hops), reducing latency.

## Privacy and Control: Pi-Hole and DoH

### The Metadata Leak
Standard DNS queries are sent in "Plain Text" over port 53. Even if you use HTTPS to browse, your ISP can still see every domain you request. 
- **DoH (DNS over HTTPS)**: Wraps the DNS request inside an encrypted HTTPS tunnel to a trusted provider (like Cloudflare), hiding your browsing destinations from your ISP.

### Pi-Hole
A "blackhole" server for network advertisements.
- **Concept**: A local server (often on a Raspberry Pi or NAS) that acts as the primary DNS for your home.
- **Filtering**: It maintains a database of ad-serving and malware domains. If a website tries to load an ad, Pi-hole returns "0.0.0.0" or a null response, preventing the ad from ever loading at the network level.
- **Integration**: By configuring a NAS to run a Pi-hole container linked to a Cloudflare `cloudflared` daemon, you gain network-wide ad-blocking + encrypted DNS (DoH).
