---
tags: [networking, security, infrastructure]
date_created: 2026-04-12
source: "[[Burlando Proxies e Firewalls ｜ Introdução a Redes Parte 5 - SSH]]"
---
# Firewalls and Proxies

## Firewalls: Kernel-Level Filtering
Firewalls run with `root` privileges to intercept all packets entering or leaving a network interface.
- **Rule Syntax**: Rules are generally composed of `Allow` or `Deny` for specific (Source IP, Port) pairs.
- **The Egress Loophole**: Most firewalls allow outgoing connections on common ports (80, 443). If a machine *inside* the network initiates a connection to an external server, the firewall considers that traffic safe and allows the server to speak back. This is how [[SSH_Tunneling|SSH tunnels]] "poke holes" in rigid firewalls.

## Web Proxies: Application-Level Intermediaries
While NAT works at the network layer, a Proxy works at the application layer (HTTP).
- **Request Structure**: In a normal request, the browser sends `GET /index.html`. In a proxied request, it sends the full URL: `GET http://www.example.com/index.html`. The proxy parses this, fetches the site, and returns it to the client.
- **Filtering**: Proxies use **Whitelists** (allow only these sites) and **Blacklists** (block these sites).
- **NAT vs. Proxy**:
  - **NAT**: Transparent translation of IP/Port headers. The destination server sees the NAT router's IP, but doesn't know a NAT is happening.
  - **Proxy**: The browser is explicitly aware of the proxy. The destination server sees the Proxy's IP.

## Bypassing Restrictions
Corporate environments often close all outgoing ports and force users through a Proxy to monitor traffic.
- **The Tunneling Solution**: Since proxies must allow *some* traffic out (usually via port 443 for HTTPS), users can encapsulate "prohibited" traffic (like SSH or unauthorized web browsing) inside a legitimate-looking stream to a remote server they control.
