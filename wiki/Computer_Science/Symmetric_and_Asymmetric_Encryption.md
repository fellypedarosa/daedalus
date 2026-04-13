---
tags: [security, cryptography, computer_science]
date_created: 2026-04-12
sources: 
  - "[[Entendendo Conceitos Básicos de CRIPTOGRAFIA ｜ Parte 1⧸2]]"
  - "[[Entendendo Conceitos Básicos de CRIPTOGRAFIA ｜ Parte 2⧸2]]"
  - "[[Akitando 54 - O Guia DEFINITIVO de UBUNTU para Devs Iniciantes.md]] (Clipper)"
  - "[[Akitando 60 - Entendendo WSL 2 | E uma curta história sobre Windows NT]] (Clipper)"
---
# Symmetric and Asymmetric Encryption

Encryption uses mathematical formulas to scramble data so that only authorized parties can decrypt it. Unlike [[Cryptographic_Hashing|hashing]], encryption is reversible.

## Symmetric Encryption
Uses a single shared secret key to both encrypt and decrypt data. The strength of symmetric ciphers lies in making brute-force computationally unfeasible.
- **DES (Data Encryption Standard)**: Deemed obsolete due to its small 56-bit key space, breakable in hours using custom FPGAs.
- **AES (Advanced Encryption Standard - Rijndael)**: Uses 128, 192, or 256-bit keys and performs multiple mathematical block transformations (S-boxes) ensuring extreme *confusion* and *diffusion*. AES is highly secure and typically hardware-accelerated directly on modern CPUs. See [[Hardware_Architecture|Hardware Architecture]].

## Asymmetric Encryption & Key Exchange
When systems need to communicate over an insecure channel without previously sharing the secret, asymmetric cryptography solves the key distribution problem.
- **Diffie-Hellman**: Based on modular arithmetic, it allows two parties to independently compute a shared secret without ever transmitting the secret itself over the wire.
- **RSA**: Relies on the difficulty of factoring massive prime numbers. While historically the standard, it requires large keys (3072+ bits) to remain secure.
- **Ed25519 (Elliptic Curve)**: A modern alternative based on Edwards-curve Digital Signature Algorithm. It is faster, more secure, and generates much smaller keys than RSA (256 bits for Ed25519 provides security equivalent to 3000-bit RSA).
- **Certificate Authorities (CAs)**: Systems use X.509 certificates signed by trusted third-party CAs (like GlobalSign or DigiCert) to avoid Man-in-the-Middle attacks during public key exchanges. See [[TLS_and_Certificate_Authorities|TLS and CAs]] and [[Digital_Signatures_and_GPG|Digital Signatures]].

## SSH Key Management

Public Key Infrastructure (PKI) is the standard for secure server access ([[SSH_Tunneling|SSH]]) and code signing ([[Git_and_Version_Control|Git]]).

### Key Pair Logic
- **Private Key (`id_ed25519`)**: Must NEVER leave the host machine. It is the "identity" of the user.
- **Public Key (`id_ed25519.pub`)**: Can be shared freely and added to a server's `authorized_keys` file or a platform like GitHub.
- **Passphrase**: An extra layer of encryption for the private key on disk. Even if the key file is stolen, it cannot be used without the passphrase.

### SSH Agent
- **The Agent (`ssh-agent`)**: A background service that stores decrypted private keys in memory.
- **Benefits**: Users only need to enter their passphrase once per session. The agent handles the signing process thereafter, preventing the need for the private key to be decrypted repeatedly on disk.
