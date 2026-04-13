---
tags: [networking, hardware, infrastructure]
date_created: 2026-04-12
source: "[[Como sua Internet Funciona ｜ Introdução a Redes Parte 3]]"
---
# Local Network Protocols (ARP & DHCP)

Underneath the abstraction of IP routing, physical local networks operate on different identification planes and hardware rules.

## DHCP (Dynamic Host Configuration Protocol)
Acts as the network manager. To prevent IP collisions—where two devices attempt to use the same internal IP and deadlock—DHCP listens for new devices entering the network and leases them an available IP address dynamically from a reserved pool.

## ARP (Address Resolution Protocol)
Within a local Ethernet environment, machines do *not* find each other via IP address. They find each other using hardware **MAC Addresses** (a permanently burned-in 48-bit identifier on the Network Interface Card). 
When a PC wants to reach a local IP, it broadcasts an ARP request across the entire network asking "Who has this IP?". The corresponding machine replies, and the PC caches its MAC Address to send direct packets thereafter.

## Hubs vs Switches
- **Hubs**: Blindly broadcast all inbound packets to all connected ports simultaneously. This exposes the network to "promiscuous mode" packet sniffing, where hijacked machines can capture neighbor traffic.
- **Switches**: Maintain a topological registry connecting specific physical ports to specific MAC Addresses, isolating traffic streams to strictly intended recipients.
