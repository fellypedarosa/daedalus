---
tags: [infrastructure, devops, orchestration, kubernetes]
date_created: 2026-04-12
sources:
  - "[[Akitando 48 - Entendendo Devops para Iniciantes em Programação (Parte 2)  Série Começando aos 40]] (Clipper)"
  - "[[Akitando 139 - Entendendo Como Containers Funcionam]] (Clipper)"
---
# Container Orchestration

While individual containers (Docker) isolate processes, managing complex microservice architectures requires **Orchestration**—the automated coordination of deployments, scaling, and networking across clusters of servers.

## Container Foundations
A container is NOT a virtual machine. Technically, it is a native process execution with restricted visibility and access, achieved via Linux kernel primitives:
1. **cgroups**: Resource limiting (CPU/RAM).
2. **Namespaces**: Process/Network isolation (PID, UTS, Network, Mount, IPC, User).
3. **Union File System (overlay2)**: Layered image storage utilizing **Copy-on-Write (COW)** to minimize disk footprint. 
   - **BTRFS Warning**: Using a BTRFS filesystem as the host for Docker's `overlay2` can lead to a "CoW on top of CoW" space explosion. Snapshots of the host filesystem while Docker is running can lead to massive disk inflation. 
   - **Optimization**: Use `chattr +C` on the Docker data directory (`/var/lib/docker`) and log directories (`/var/log`) to disable the CoW attribute for those specific paths, effectively turning BTRFS into a non-CoW storage for those blocks.
4. **Capabilities**: Restricted root privileges (e.g., `CAP_NET_BIND_SERVICE` for ports < 1024).

## The OCI Stack (Standardization)
The **Open Container Initiative (OCI)** maintains standards for interoperability:
- **Image Spec**: Defines the format of filesystem layers and metadata (OCI images are essentially layered tarballs).
- **Runtime Spec**: Defines how to unpack and execute these images.
- **runC**: The industry-standard reference implementation of the OCI runtime. It executes the low-level logic (namespaces, cgroups) defined in a `config.json`.
- **containerd**: A high-level daemon that manages container lifecycles (transferring images, managing storage). Used as the default runtime for **Docker** and **Kubernetes**.

## Container Engines
- **Docker**: A developer-centric platform. Uses a root-level daemon (`containerd`) to manage lifecycle.
- **Podman**: A daemonless, **rootless** alternative. By default, it interacts directly with `runC` and does not require elevated privileges, making it inherently more secure.

## Layered Images and Optimization
Images are built in layers corresponding to commands in a `Dockerfile`.
- **Squashing**: To keep images small, temp files should be deleted within the same `RUN` command (commit) to avoid them being persisted in an intermediary layer.
- **Reproducibility**: Always fix versions (e.g., `node:lts` or `postgres:15`) to ensure dev/prod parity.

## Deployment and Orchestration Tools

### Docker Compose
Designed for single-node developer productivity, Docker Compose serves as **living documentation** for a project's local infrastructure.
- **`docker-compose.yaml`**: Defines services (API, DB, Cache), volumes, and dependencies.
- **`depends_on`**: Ensures the startup order (e.g., DB must be healthy before API boots), though it doesn't guarantee the application inside is ready (use healthchecks for that).
- **Environment Parity**: Mapping local volumes for development (`- .:/app`) versus copying them into the image for production.

### Networking Modes
1. **Bridge (Default)**: Creates a virtual network bridge. Containers get virtual IPs and communicate via a NAT layer. 
   - **Pros**: Isolation, port mapping. 
   - **Cons**: Overhead. In high-stress load testing, the virtual NAT can become a bottleneck (manifesting as `IOException: Premature Close`).
2. **Host**: The container shares the host's network namespace directly.
   - **Pros**: Highest performance (near-native). Required for accurate hardware-level benchmarking.
   - **Cons**: No isolation. Containers must use unique ports on the host. Not available natively on Docker for Mac/Windows (requires a Linux VM/WSL2).

### The Modern Orchestration Standard: Kubernetes (K8s)
Originally developed by Google, Kubernetes coordinates "Pods" (groups of containers), service discovery, and zero-downtime rolling updates across elastic, multi-node production infrastructure.

## Alternatives and Evolution
- **Docker Swarm**: A simpler, native clustering tool for Docker.
- **Platform as a Service (PaaS)**: Tools like **Heroku** demonstrated a viable developer-centric model for deployment, which influenced the design of Kubernetes and the GKE/EKS/AKS services provided by cloud vendors.
