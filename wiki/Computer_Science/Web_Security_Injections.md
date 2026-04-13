---
tags: [security, hacking, development]
date_created: 2026-04-12
source: "[[Burlando Proxies e Firewalls ｜ Introdução a Redes Parte 5 - SSH]]"
---
# Web Security Injections

A fundamental axiom of development is that any incoming string from external clients is malicious and structurally contaminated by definition until properly **sanitized**. See [[Information_Security_and_Human_Factor|Information Security]] for the human factors that enable these attacks.

## Case Study: The "Cowsay" Scenario
A common junior mistake is building "CGI-like" functionality by calling external system utilities. 
- **The Setup**: A Node.js or Ruby script receives a `?message=` query param and executes `child_process.exec("cowsay " + message)`.
- **The Exploit**: An attacker sends `?message=hello;ls -la`. The shell interprets the semicolon as a command separator, executing `cowsay hello` followed by `ls -la`.
- **Escalation**: Attackers can use this to read private keys (`cat ~/.ssh/id_rsa`), list environment variables, or install web shells. See [[Symmetric_and_Asymmetric_Encryption#SSH Key Management|SSH Key Management]] and [[Shell_Mechanics|Shell Mechanics]].

## Sanitization Strategy
Treating all external input as "radioactive material" is the only sustainable security posture.

### 1. Character Stripping (The Drastic Approach)
Using regular expressions to permit ONLY specific characters:
```javascript
function sanitize(input) {
  // Removes everything that isn't a letter or number
  return input.replace(/[^a-zA-Z0-9]/g, "");
}
```
*Note: This is drastical and breaks punctuation, but effectively kills all shell injection characters like `;`, `&`, `|`, `$`, and `(`.*

### 2. Escaping (The Standard Approach)
Using libraries to escape special characters so the shell interprets them as literal strings rather than control characters.

### 3. Entry Point Hygiene
Security doesn't mean being paranoid in every internal function. 
- **Entry Points**: Only functions directly receiving user data (Web Controllers, API endpoints) require heavy sanitization.
- **Internal Functions**: Should assume the data they receive has already been sanitized or is from a trusted source to avoid performance bloat and redundant logic (Defensive coding in excess is anti-pattern). See [[Web_Architecture_and_Scalability|Web Architecture]] and [[Firewalls_and_Proxies|Firewalls]] for additional defense layers.
