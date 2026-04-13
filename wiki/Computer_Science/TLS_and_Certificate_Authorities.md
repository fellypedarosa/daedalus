---
tags: [security, networking, cryptography]
date_created: 2026-04-12
sources: 
  - "[[Criptografia na Prática - Certificados, BitTorrent, Git, Bitcoin]] (YouTube)"
  - "[[Akitando 147 - Criptografia na Prática - Certificados, BitTorrent, Git, Bitcoin]] (Clipper)"
---
# TLS and Certificate Authorities

To prevent Man-in-the-Middle (MitM) attacks during [[Symmetric_and_Asymmetric_Encryption|asymmetric key exchanges]] via a public network, clients must definitively verify that the supplied Public Key belongs to the intended entity (e.g. Amazon) and not an intervening malicious actor.

## The Chain of Trust
Modern Operating Systems and web browsers securely pre-package Root Certificates from trusted Certificate Authorities (CAs) like Let's Encrypt, DigiCert, or Google Trust Services (e.g. `ISRG Root X1`).
- When a browser connects to a web server via HTTPS, the server replies with a Digital Certificate (`fullchain.pem`), a structured metadata file containing the server's Public Key, domain identity, and an attached **[[Digital_Signatures_and_GPG|Digital Signature]]**.
- This Digital Signature is a [[Cryptographic_Hashing|cryptographic hash]] of the certificate himself, encrypted using the CA's intermediate Private Key. 
- Because the browser implicitly trusts the pre-installed Root CA, it can decrypt the metadata's signature using the CA's public profile. If the resultant hash matches the certificate body, the server's identity is mathematically validated, mitigating impersonation vectors.

## Automated Certificate Provisions (Certbot)
System administrators can automate the signing process through protocols like ACME (used by Let's Encrypt/Certbot). The server solves an ownership challenge (usually exposing a specific TXT record in the [[DNS_and_Resolution|DNS registrar]] or a local `.well-known` HTTP endpoint), proving authoritative control over the domain in exchange for a temporarily valid, signed `.pem` keypair. See [[Web_Architecture_and_Scalability|Web Architecture]] for deployment context.
