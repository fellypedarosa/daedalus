---
tags: [security, cryptography, identity]
date_created: 2026-04-12
sources: 
  - "[[Sua Segurança é uma DROGA ｜ Gerenciadores de Senhas, 2FA, Encriptação]]"
---
# Multi-Factor Authentication and TOTP

Multi-Factor Authentication (MFA) relies on asserting identity across three distinct domains: Knowledge (what you know, e.g. a password), Possession (what you have, e.g. a token), and Inherence (what you are, e.g. biometrics). See [[Information_Security_and_Human_Factor|Information Security]] for social engineering risks.

## Time-Based One-Time Password (TOTP) Mechanics
Under RFC 6238, common Authenticator apps operate on entirely offline cryptographic derivatives without needing internet connectivity or central signaling (unlike SMS vectors which are highly vulnerable to Social Engineering SIM-swapping attacks).
- **The Seed Parameter**: Initializing MFA provisions a shared Secret Seed (typically embedded via QR Code) existing symmetrically on the authentication server and the client's cryptoprocessor. See [[Symmetric_and_Asymmetric_Encryption|Symmetric Encryption]].
- **HMAC-SHA1 Execution**: The standard combines the exact synchronous system time (rounded to 30 or 60-second execution windows) mapped against the Seed, passing it through an HMAC-SHA1 algorithm. This derives a deterministic [[Cryptographic_Hashing|hash]], which is ultimately truncated to a standard 6-digit confirmation pin.

## Hardware Secure Enclaves
To prevent the Seed string or biometric profiles from being intercepted by hostile Kernels and memory-dump Malware, high-level Possession and Inherence factors securely silo these cryptographic routines inside dedicated coprocessors (like Apple's T2 Enclave or Intel/AMD's TPM modules), entirely air-gapping the primary OS from the validation variables.
