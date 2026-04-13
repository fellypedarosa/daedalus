---
tags: [networking, concepts, telecom]
date_created: 2026-04-12
source: "[[Introdução a Redes： Como Dados viram Ondas？ ｜ Parte 1]]"
---
# Circuit vs Packet Switching

These represent the two fundamental paradigms of telecommunication routing history.

## Circuit Switching
Historically used by telephone switchboards and early dial-up modems. In this model, establishing a connection creates a dedicated, stateful, point-to-point physical (or logical) circuit between sender and receiver. 
- **Drawback**: Wastes bandwidth. If neither party is transmitting data, the line remains locked and unusable by others.

## Packet Switching
Modern networks (e.g., the Internet) operate statelessly. Data is fragmented into fixed-size blocks called "packets" (or datagrams).
- **Routing**: Each packet is tagged with metadata (like IP address and sequence number).
- **Multiplexing**: Packets from completely different users and applications can travel interleavingly across the same physical cable simultaneously, maximizing bandwidth efficiency.
- **Reassembly**: The receiver acknowledges (`ACK`) valid packets, requests retransmission of corrupted ones (`NAK`), and reassembles them in the correct order.
