---
tags: [networking, hardware, infrastructure]
date_created: 2026-04-12
sources:
  - "[[Introdução a Redes： Como Dados viram Ondas？ ｜ Parte 1]]"
  - "[[Akitando 60 - Entendendo WSL 2 | E uma curta história sobre Windows NT]] (Clipper)"
---
# Networking Fundamentals

A network is constructed upon various physical mediums, historical protocols, and modulation techniques to transport digital data (bits) across distances.

## Signals and Waves
Digital data (bits) cannot travel through air or copper in its raw square-wave state over long distances. It must be converted into analog waves.
- **Modulation**: The process of encoding digital information into an analog signal (e.g., varying amplitude, frequency, or phase). See [[Modulation_and_Demodulation|Modulation and Demodulation]].
- **Demodulation**: The reverse process at the receiving end.
- **Modem (MOdulator-DEModulator)**: The hardware responsible for this transformation.

### Frequency and Bandwidth
- **Low Frequency (2.4 GHz)**: Long waves that penetrate solid objects (walls) better but carry less data per second.
- **High Frequency (5 GHz / 60 GHz mmWave)**: Short waves that carry massive amounts of data but are easily blocked by rain, walls, or even human hands.
- **Marketing Factor of 8**: ISPs sell "Mega" bits (Mb), but software measures Mega Bytes (MB). To find your true download speed, divide the ISP's number by 8.

## Switching Paradigms

### Circuit Switching (The Telephony Model)
- **Mechanism**: Establishes a dedicated, physical path between two points for the duration of the communication.
- **Stateful**: The network must maintain the state of the connection. If a wire is cut, the connection drops.
- **Efficiency**: Low. Resources are reserved even if no data is being transmitted (silence on a phone call).

### Packet Switching (The Internet Model)
See [[Circuit_vs_Packet_Switching|Circuit vs Packet Switching]] for a deeper comparison.
- **Mechanism**: Breaks data into small "packets," each containing the destination address. Packets can take different routes to reach the same destination.
- **Stateless**: The core network doesn't care about the "connection," only about routing individual packets.
- **Efficiency**: High. Multiple users can share the same physical cable simultaneously by interleaving their packets. This forms the basis of the [[OSI_and_TCPIP_Models|TCP/IP Model]].

## Multiplexing (Sharing the Medium)
- **TDM (Time Division Multiplexing)**: Each user gets a specific time slot on the wire.
- **FDM (Frequency Division Multiplexing)**: Each user gets a specific frequency band (like radio stations).

## Practical Networking: The WSL2 Case

Modern virtualization introduces complex networking scenarios, specifically in Windows Subsystem for Linux (WSL2):

### Virtual NAT
WSL2 runs in a lightweight VM. Unlike WSL1 (which used a bridge to share the Windows IP), WSL2 uses **[[IP_Addresses_and_NAT|NAT (Network Address Translation)]]**.
- **Internal IP**: WSL2 has its own virtual IP address, making it invisible to the local network by default.
- **Port Mapping**: Windows automatically maps `localhost` to the WSL2 IP, but conflicts can occur if Windows services are already using the same ports.

### GUI and DISPLAY Routing
To run a Linux GUI application (X11) inside WSL2 and display it on Windows:
- A local X Server (e.g., VcXsrv, GWSL) must run on Windows.
- The `DISPLAY` environment variable in Linux must point to the **host's IP** (since `localhost` inside the VM refers to the VM itself).
- **Automation**: `export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0`.
