---
tags: [networking, ssh, security]
date_created: 2026-04-12
source: "[[Burlando Proxies e Firewalls ｜ Introdução a Redes Parte 5 - SSH]]"
---
# SSH Tunneling (Port Forwarding)

Secure Shell (SSH) allows the projection of secure tunnels that completely circumvent strict NATs and restrictive firewalls.

## The "Poking a Hole" Concept
A rigid firewall drops any incoming connection from the internet. However, since the firewall allows *outbound* requests, a local client can initiate a connection to an external VPS. Once that bridge is formed, the external server can freely converse backwards through the established connection state, "poking a hole" through the firewall.

## Tunneling Modes

### 1. Remote Forwarding (`-R`)
**Goal**: Expose a local service to the internet.
- **Scenario**: You have a web app on `localhost:3000` behind a rigid firewall.
- **Command**: `ssh -R 8080:127.0.0.1:3000 user@vps`
- **Result**: People visiting `vps:8080` are tunneled to your local machine.
- **Dependency**: The VPS `sshd_config` must have `GatewayPorts yes` enabled for the port to be public.

### 2. Local Forwarding (`-L`)
**Goal**: Access a remote service as if it were local.
- **Scenario**: A database on a remote server is only listening on `127.0.0.2:5432`.
- **Command**: `ssh -L 9000:127.0.0.2:5432 user@vps`
- **Result**: You connect to `localhost:9000` on your machine, and the traffic is tunneled to the remote DB.

### 3. Dynamic Forwarding (`-D`)
**Goal**: Create a personal Proxy (SOCKS5).
- **Scenario**: Bypassing a restrictive company proxy or geo-blocking.
- **Command**: `ssh -D 1337 user@vps`
- **Result**: Your machine acts as a SOCKS5 proxy on port 1337. All traffic sent there is tunneled through the VPS and exits to the internet from its IP.

## Evasion Strategies
- **Port Swapping**: If a firewall blocks port 22 (SSH), reconfigure the remote `sshd` to listen on port 80 or 443. Since firewalls must allow web traffic, the SSH connection (and its tunnels) will often pass through undetected.
- **Encryption**: Because SSH is encrypted, the firewall or corporate proxy cannot see *what* is inside the tunnel (e.g., they can't see you're browsing Netflix or accessing a private NAS).
