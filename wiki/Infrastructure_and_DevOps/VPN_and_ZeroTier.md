---
tags: [networking, vpn, infrastructure]
date_created: 2026-04-12
sources:
  - "[[Criando uma Rede Segura ｜ Introdução a Redes Parte 6 - VPN e NAS]] (YouTube)"
  - "[[Akitando 126 - Criando uma Rede Segura  Introdução a Redes Parte 6 - VPN e NAS]] (Clipper)"
---
# VPN & Virtual Network Interfaces

Virtual Private Networks (VPNs) simulate localized environments over the wider public internet securely. To accomplish this, they map logic directly into the OS routing tables via dummy devices that impersonate physical networking hardware.

## Virtualization and The "Matrix" Metaphor
To the operating system, it doesn't matter if hardware is physical or virtual. If a driver exists, the OS believes it is real.
- **Hypervisors**: Use virtual NICs to let Guest OSs (like a Windows VM) think they have a dedicated ethernet card.
- **VPNs**: Use virtual drivers to create a "tunnel" through the internet that acts like a local physical cable.

## TUN and TAP Drivers
- **TUN (Network Layer)**: Handles IP packets (Layer 3). Most VPNs (OpenVPN, Wireguard) use this to create simple tunnels between machines.
- **TAP (Data Link Layer)**: Handles Ethernet frames (Layer 2). Used when you need to bridge networks at a deeper level (e.g., in virtualized data centers).

## VPN Models
1. **Remote Access (Client-to-Site)**: A worker connects their laptop to the company's VPN server to access internal files.
2. **Site-to-Site (Gateway-to-Gateway)**: Two routers connect to each other via a permanent VPN tunnel, allowing two separate office networks to act as a single unit.

## Modern VPN Architectures

### Software Defined Networking (SDN)
Tools like **ZeroTier** and **Tailscale** simplify VPNs by managing the routing logic in the cloud. They automatically handle NAT traversal (hole poking) so you don't have to manually configure ports.
- **ZeroTier**: Creates an virtual "Ethernet Switch" in the cloud. Every device you join is on the same private LAN, regardless of physical location.

### Protocol Comparison
- **PPTP**: Obsolete and insecure. Do not use.
- **OpenVPN**: The old industry standard. Versatile but computationally "heavy" (lots of code, slower).
- **Wireguard**: The modern standard. Extremely fast, lightweight, and built directly into the Linux kernel. It uses modern cryptography and is significantly more efficient than OpenVPN.
