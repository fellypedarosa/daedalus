---
tags: [security, cryptography]
date_created: 2026-04-12
sources: 
  - "[[Criptografia na Prática - Certificados, BitTorrent, Git, Bitcoin]] (YouTube)"
  - "[[Akitando 147 - Criptografia na Prática - Certificados, BitTorrent, Git, Bitcoin]] (Clipper)"
---
# Digital Signatures and GPG

[[Cryptographic_Hashing|Cryptographic hashing]] (like SHA-512) guarantees data structural integrity but does NOT inherently guarantee origin authenticity. A Man-in-the-Middle could transparently swap a malicious binary and subsequently replace the published SHA-512 text file to match the new payload.

## The Validation Mechanism
To prevent origin spoofing, entities rely on **Digital Signatures** using asymmetric keypairs (like OpenPGP/GPG).
1. The author computes the deterministic hash of the target payload (e.g. an ISO OS image).
2. The author mathematically encrypts that raw hash string *using their Private Key*, generating a proprietary `.sig` binary file.
3. Because Public Keys can decrypt strings locked by a corresponding Private Key, the end-user uses tools like `gpg --verify` alongside the author's recognized Public Key (imported via a keychain) to decrypt the `.sig`.
4. If the decrypted hash matches the user's localized hash of the downloaded payload, cryptographic guarantees assert that the file natively originated from the owner of the Private Key and remains bit-perfect.
