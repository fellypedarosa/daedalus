"""Simple lexical baseline; evaluation only, never used by production."""
from pathlib import Path
import re

SKIP_FILES = {"index.md", "log.md", "Ingestion_Tracker.md"}

PT_EN_MAP = {
    # CS fundamentals
    "memória": "memory", "memoria": "memory",
    "gerenciamento": "management", "compilador": "compiler",
    "compiladores": "compilers", "algoritmo": "algorithm",
    "algoritmos": "algorithms", "criptografia": "cryptography",
    "criptográfico": "cryptographic", "hash": "hash",
    "assinatura": "signature", "assinaturas": "signatures",
    "certificado": "certificate", "certificados": "certificates",
    "chave": "key", "chaves": "keys",
    "encriptação": "encryption", "cifra": "cipher",
    "descriptografar": "decrypt", "simétrica": "symmetric",
    "assimétrica": "asymmetric",
    # Networking
    "rede": "network", "redes": "networks",
    "roteamento": "routing", "roteador": "router",
    "firewall": "firewall", "proxy": "proxy",
    "túnel": "tunnel", "tunelamento": "tunneling",
    "porta": "port", "portas": "ports",
    "soquete": "socket", "soquetes": "sockets",
    "endereço": "address", "dns": "dns",
    "protocolo": "protocol", "protocolos": "protocols",
    "pacote": "packet", "pacotes": "packets",
    "camada": "layer", "camadas": "layers",
    # Infrastructure
    "contêiner": "container", "contêineres": "containers",
    "container": "container", "containers": "containers",
    "virtualização": "virtualization",
    "armazenamento": "storage",
    "sistema de arquivos": "filesystem",
    "implantação": "deployment",
    "servidor": "server", "servidores": "servers",
    "nuvem": "cloud", "orquestração": "orchestration",
    # OS
    "sistema operacional": "operating system",
    "kernel": "kernel", "processo": "process",
    "processos": "processes", "segurança": "security",
    "inicialização": "boot", "permissão": "permission",
    "permissões": "permissions", "usuário": "user",
    # Programming
    "linguagem": "language", "linguagens": "languages",
    "programação": "programming", "paradigma": "paradigm",
    "concorrência": "concurrency", "paralelo": "parallel",
    "paralelismo": "parallelism", "thread": "thread",
    "banco de dados": "database",
    "consulta": "query", "índice": "index",
    # General
    "desempenho": "performance", "hardware": "hardware",
    "software": "software", "arquitetura": "architecture",
    "distribuição": "distribution", "licença": "license",
    "código aberto": "open source", "projeto": "project",
    "erro": "error", "correção": "correction",
    "redundância": "redundancy", "recuperação": "recovery",
    "malware": "malware", "ransomware": "ransomware",
}

def _expand_query(query: str) -> str:
    """Expand a query by translating Portuguese terms to English.

    Returns a combined query with both original and translated terms,
    giving English terms a natural advantage in scoring.
    """
    lower = query.lower()
    extra_terms = []

    # Try multi-word phrases first (longer matches take priority)
    for pt, en in sorted(PT_EN_MAP.items(), key=lambda x: -len(x[0])):
        if pt in lower:
            extra_terms.append(en)
            lower = lower.replace(pt, "")  # avoid double-matching substrings

    # Try remaining single words
    for word in query.lower().split():
        if word in PT_EN_MAP and PT_EN_MAP[word] not in extra_terms:
            extra_terms.append(PT_EN_MAP[word])

    if extra_terms:
        return f"{query} {' '.join(extra_terms)}"
    return query

def search(root: Path, query: str, limit: int = 10) -> list:
    """Pure filesystem full-text search with relevance scoring and PT→EN expansion."""
    expanded = _expand_query(query)
    terms = expanded.lower().split()
    results = []

    for md in (root / "wiki").rglob("*.md"):
        if md.name in SKIP_FILES:
            continue
        content = md.read_text(errors="replace")
        lower = content.lower()
        title = md.stem.replace("_", " ").lower()

        score = 0
        matches = []

        for term in terms:
            # Title match = 10 points each
            if term in title:
                score += 10
            # Content frequency
            count = lower.count(term)
            score += count

            # Extract context snippets around matches
            for m in re.finditer(re.escape(term), lower):
                start = max(0, m.start() - 80)
                end = min(len(content), m.end() + 80)
                snippet = content[start:end].strip().replace("\n", " ")
                line = content[: m.start()].count("\n") + 1
                matches.append({"line": line, "text": f"...{snippet}..."})

        if score > 0:
            # Deduplicate match snippets
            seen = set()
            unique = []
            for match in matches:
                key = match["text"][:100]
                if key not in seen:
                    seen.add(key)
                    unique.append(match)

            results.append(
                {
                    "file": str(md.relative_to(root)),
                    "score": score,
                    "matches": unique[:4],
                }
            )

    results.sort(key=lambda x: -x["score"])
    return results[:limit]
