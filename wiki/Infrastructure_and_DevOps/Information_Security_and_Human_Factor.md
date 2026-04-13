---
tags: [security, infosec, devops, social_engineering]
date_created: 2026-04-12
sources: 
  - "[[RANT： Selo de Segurança é Marketing ｜ Entendendo o Fator Humano]] (YouTube)"
  - "[[Akitando 88 - RANT Selo de Segurança é Marketing  Entendendo o Fator Humano]] (Clipper)"
---
# Information Security and the Human Factor

The greatest vulnerability in any infrastructure is never solely cryptographic; it is fundamentally human. See [[MFA_and_TOTP|MFA]] for authentication hardening and [[Malware_and_Ransomware_Defenses|Malware Defenses]] for endpoint protection.

## Fallacy of "Hacker" Stereotypes
The majority of corporate breaches are not executed via complex zero-day exploit kernels. Over 90% of significant data breaches (like the 2020 Twitter phone spear-phishing incident) stem from Social Engineering.
- **Phishing**: Manipulating employees into surrendering credentials naturally via emails simulating legitimate authorities.
- **Arrogance and Negligence**: Developers inadvertently hardcoding credentials, leaving ports exposed, or bypassing ORMs in the name of marginal performance gains. See [[Web_Security_Injections|Web Security Injections]] and [[Cryptographic_Hashing#Password Storage Strategies|Password Storage]].

## Governance and Liability
For large-scale corporations, Information Security merges with Compliance (Infosec).
- **The True Purpose of Compliance**: Frameworks like ITIL, SOX (Sarbanes-Oxley), and COBIT exist to delineate legal responsibility and strict process boundaries, rather than guaranteeing mathematical "invulnerability".
- **Mitigation vs Perfection**: Absolute 100% security requires an offline topology. Practical DevSecOps accepts that breaches *will* happen. Success means implementing deep contingency plans, stringent backups, automated incident responder frameworks, and ruthlessly minimizing individual employee autonomy in deployment environments.
