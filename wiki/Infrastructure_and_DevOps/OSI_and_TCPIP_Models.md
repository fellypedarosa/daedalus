---
tags: [networking, infrastructure, models]
date_created: 2026-04-12
source: "[[Como sua Internet Funciona ｜ Introdução a Redes Parte 3]]"
---
# OSI and TCP/IP Models

To understand network communication, two distinct abstraction models exist: **TCP/IP** (which is what practical modern networks actually use) and **OSI** (which is the classic 7-layer academic model used to explain how networks operate).

## OSI vs. TCP/IP: The Practical Distinction
- **OSI (Open Systems Interconnection)**: A "useful model" for academics. It separates concerns into 7 distinct layers to explain the stack.
- **TCP/IP**: The "useful protocol." It consolidated the stack into 4 practical layers (Network Access, Internet, Transport, and Application) because in the real world, the "Session" and "Presentation" layers are largely handled by the Application layer itself.

## Encapsulation: The Matryoshka Principle
As data travels down the stack, each layer wraps the payload from the layer above in its own "header" (metadata).
1. **Application**: Generates the raw message (e.g., HTTP GET). See [[Sockets_and_Ports|Sockets and Ports]].
2. **Transport (TCP/UDP)**: Adds a header (Ports, Sequence numbers). The payload is now a **Segment**.
    - **TCP Handshake & State**: TCP is connection-oriented. It establishes a formal, stateful "Handshake" (like a Dial-up modem's synchronization phase or a [[TLS_and_Certificate_Authorities|TLS]] cryptographic handshake) before transmitting. It ensures guaranteed delivery via acknowledgments and buffer management (Sliding Windows) to prevent network congestion.
3. **Network**: Adds an IP header (Source/Dest IP). The payload is now a **Packet**. See [[IP_Addresses_and_NAT|IP Addresses and NAT]].
4. **Data Link**: Adds a Frame header (Source/Dest MAC) and a CRC trailer for [[Error_Correction_Codes|error checking]]. The payload is now a **Frame**.
5. **Physical**: Transmits the frame as a stream of electrical/optical signals (Bits). See [[Networking_Fundamentals|Networking Fundamentals]] and [[Modulation_and_Demodulation|Modulation]].

On the receiving end, the process is reversed (**Decapsulation**), where each layer "unwraps" its specific header and passes the remainder up the stack.

## Layer 5 & 6: The "Ghost" Layers
In modern software engineering, layers 5 (Session) and 6 (Presentation) don't usually exist as separate network entities.
- **Session**: Handled by HTTP/HTTPS or application-level socket management.
- **Presentation**: Handled by MIME types, JSON serialization, and TLS (encryption) at the application level.

This abstraction allows for **Modularity**: You can switch from 4G to Fiber (Physical/Data Link swap) without the browser (Application) ever noticing the change.
