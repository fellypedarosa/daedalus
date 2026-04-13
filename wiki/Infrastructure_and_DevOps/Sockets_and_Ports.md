---
tags: [networking, infrastructure, sockets]
date_created: 2026-04-12
source: "[[Como Funciona Sockets, Cliente, Servidor e a Web？ ｜ Introdução a Redes Parte 4]]"
---
# Sockets and Ports

A **Socket** is the fundamental Inter-Process Communication (IPC) primitive that establishes network connections. Since [[Memory_Management|Virtual Memory]] isolates processes completely, one process cannot read another's memory. Instead of using file pipes, networks rely on Sockets to transfer bitstreams across domains. Sockets operate at the [[OSI_and_TCPIP_Models|Transport Layer]] of the network stack.

## IPC and Process Isolation
Because of **Virtual Memory**, one process cannot simply reach into another process's memory space. To communicate, they use **Inter-Process Communication (IPC)**:
- **Files**: One writes, another reads (slow, storage-dependent).
- **Pipes**: Serial data transfer (local only).
- **Sockets**: Network-capable streams defined by the (IP:Port) tuple.

## Port Classifications
Ports are 16-bit identifiers (0 - 65535) used to direct packets to specific processes.
- **System/Reserved (0–1023)**: Standardized services. Binding to these requires `root` or `Admin` privileges (e.g., HTTP: 80, HTTPS: 443, [[SSH_Tunneling|SSH]]: 22, [[DNS_and_Resolution|DNS]]: 53). See [[Operating_System_Internals#Linux Capabilities|Linux Capabilities]] for fine-grained port binding.
- **User/Registered (1024–49151)**: Common development ranges. Applications like Node.js (3000) or Databases like Postgres (5432) live here.
- **Dynamic/Ephemeral (49152–65535)**: Temporary ports assigned by the OS for client-side connections (e.g., when your browser opens a socket to talk to a server).

## Server Lifecycle: The "Big Loop"
A server is essentially a long-lived process running an infinite loop to handle connections:
1. **Bind**: The process requests the OS to "claim" a specific port.
2. **Listen**: The OS starts queuing incoming packets for that port.
3. **Accept**: The process takes the first connection in the queue. This is a "blocking" operation—the process stops here until someone connects.
4. **Data Exchange**: The process reads the request (Input), performs logic (Processing), and writes the response (Output).
5. **Close/Continue**: The process closes the connection or keeps it open (Keep-Alive) and returns to step 3.

## Address Binding: Localhost vs. Everywhere
- **`127.0.0.1` (localhost)**: The service is only accessible from the machine itself.
- **`0.0.0.0`**: The service listens on *all* available network interfaces (WiFi, Ethernet, [[VPN_and_ZeroTier|VPN]]). Useful for making a dev server accessible to other devices on the LAN. See [[Firewalls_and_Proxies|Firewalls]] for controlling access.
