---
tags: [security, cryptography, hashing]
date_created: 2026-04-12
sources: 
  - "[[Entendendo Conceitos Básicos de CRIPTOGRAFIA ｜ Parte 1⧸2]]"
  - "[[Entendendo Conceitos Básicos de CRIPTOGRAFIA ｜ Parte 2⧸2]]"
---
# Cryptographic Hashing

Unlike [[Symmetric_and_Asymmetric_Encryption|encryption]], Hashing is a one-way (irreversible) function that maps arbitrary-sized data to a fixed-size bit string (digest). A hash serves as a digital fingerprint. It underpins [[Digital_Signatures_and_GPG|Digital Signatures]], [[MFA_and_TOTP|TOTP/MFA]], [[Git_Algorithms_and_Internals|Git internals]], and [[Merkle_Trees_and_DAGs|Merkle Trees]].

## Vulnerabilities in Legacy Algorithms
Early algorithms like **MD5** and **SHA1** are mathematically broken and highly vulnerable to:
- **Collision Attacks**: Two entirely different inputs producing the exact same hash (violating uniqueness requirements).
- **Length Extension Attacks**: Adversaries can extrapolate the mathematical state of the digest and append malicious payloads while calculating a structurally valid signature.

## Password Storage Strategies
Storing plaintext passwords or simply hashing them is fundamentally flawed. Hackers use precomputed *Rainbow Tables* or custom ASIC/GPU clusters to iterate billions of combinations per second. Standard high-speed hash functions (like **SHA512**) are detrimental for password storage precisely because their computational efficiency allows parallelized GPUs to iterate over dictionaries too fast.
- **Salting**: Appending unique random strings to passwords before hashing defeats static rainbow tables.
- **Key Derivation (PBKDF2, Bcrypt, Argon2)**: Intentionally slow algorithms designed to drain computational power and memory resources. Algorithms like `Bcrypt` use Blowfish block ciphers requiring significant RAM initialization, starving ASIC setups from performing mass parallel brute-forcing. See [[Information_Security_and_Human_Factor|Information Security]] for the human side of password failures.

### Entropy and Leetspeak Fallacy
Adding dictionary-derived mutations (leetspeak, e.g. mapping `a` -> `@`, `i` -> `1`) does *not* result in a strong password. These predictable permutations are pre-computed within massive database Rainbow Tables (upwards of terabytes in size). Cryptographically resilient authentication strictly requires long, true-random generative passwords where the length increases collision bounds exponentially (e.g. 92 character map combinations).

**Note:** Formats like Base64 or CRC are NOT encryption nor cryptographic hashing. They strictly exist for protocol encoding and simple transmission [[Error_Correction_Codes|error checking]].
