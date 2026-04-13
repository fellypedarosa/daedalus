---
tags: [linux, operating_systems, administration]
date_created: 2026-04-12
sources:
  - "[[Akitando 127 - Como Funciona o Boot de um Linux  O que tem num LiveCD]] (Clipper)"
---
# Systemd and Service Management

Systemd is the contemporary initialization system and service manager for Linux, replacing the traditional SysV init standard. It acts as the backbone of the OS, managing process lifecycles and system states.

## Runlevels vs. Targets
In the traditional **SysV Init** model, the system state was defined by numerical **Runlevels** (0-6). Systemd replaces these with **Targets**.
- **Runlevel 3 (multi-user.target)**: A full console-based system with networking and multiple users, but no graphical interface.
- **Runlevel 5 (graphical.target)**: The standard desktop environment including the Display Manager (e.g., GDM).
- **Runlevel 0 (poweroff.target)**: The state for a graceful shutdown.

## Control Interface: systemctl
The primary utility for interacting with systemd is `systemctl`.
- `systemctl start [service]`: Immediate execution of a service.
- `systemctl enable [service]`: Configures a service to start automatically on boot.
- `systemctl status [service]`: Displays process health and logs.
- `systemctl get-default`: Shows the current default boot target.
- `systemctl set-default multi-user.target`: Changes the boot mode to permanent CLI.

## System Integrity and Graceful Shutdown
Proper service management is critical for data integrity. A **Graceful Shutdown** (`shutdown -h now`) notifies all running processes via signal interrupts (SIGTERM) to flush file buffers and close log handles. Forced resets (reset button) bypass this safety mechanism, significantly increasing the risk of filesystem or database corruption.
