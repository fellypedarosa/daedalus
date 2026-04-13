---
tags: [networking, infrastructure, addressing]
date_created: 2026-04-12
source: "[[Como sua Internet Funciona ｜ Introdução a Redes Parte 3]]"
---
# IP Addressing and NAT

Internet architecture has navigated a historic bottleneck regarding address scarcity, mediated heavily by Network Address Translators (NAT). Operates at the [[OSI_and_TCPIP_Models|Network Layer]] of the TCP/IP stack.

## Subnets and Masks: The Bitwise Logic
- **Subnet Mask**: A bitmask used to determine which part of the IP address refers to the network and which part refers to the host.
- **CIDR Notation**: A shorthand way to write masks. For example, `/24` means the first 24 bits (out of 32) are the network prefix (`255.255.255.0`).
- **Bitwise AND**: Computers perform a logical AND between their IP and the Subnet Mask. If the resulting network ID matches the destination's network ID, the packet is local. If not, it is sent to the **Default Gateway**. See [[Firewalls_and_Proxies|Firewalls]] for packet filtering.

## Private Address Ranges
Reserved ranges that cannot be routed on the public internet:
- `10.0.0.0` - `10.255.255.255` (Class A)
- `172.16.0.0` - `172.31.255.255` (Class B)
- `192.168.0.0` - `192.168.255.255` (Class C - most home routers)

## NAT: The PBX Metaphor
Think of an office with one main phone number (Public IP) but many departments with their own internal extensions (Private IPs).
- **Inward**: The "operator" (NAT) receives a call and checks a table to see which extension it belongs to.
- **Outward**: An extension calls out; the operator notes down who is calling (Source IP/Port) so they can route the reply back to the right desk.
- **NAT Table**: The router's internal log mapping (Private IP:Port) to (Public IP:Port).

## IPv4 Scarcity and CGNAT
Because we ran out of IPv4 addresses, ISPs use **Carrier-Grade NAT (CGNAT)**.
- **The "NAT inside a NAT" Problem**: Your home router (NAT 1) gets a private address from the ISP, who then uses another NAT (NAT 2) to translate that to a real public IP.
- **Consequence**: Shared IP reputation (if one person on the ISP is banned, you might be too) and the impossibility of opening ports for local servers ([[NAS_Architecture|NAS]], Game hosting) without tunneled workarounds like [[VPN_and_ZeroTier|VPNs]] or [[SSH_Tunneling|SSH Tunneling]].

## IPv6: Scalability as Architecture
IPv6 doesn't just "add numbers"; it removes the need for NAT entirely through sheer scale ($3.4 \times 10^{38}$ addresses). 
- **The "Success" of IPv4**: Ironically, NAT was *too* successful as a band-aid, delaying global IPv6 adoption for decades because "it just works."
