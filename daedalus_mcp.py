#!/usr/bin/env python3
"""
daedalus_mcp.py — MCP Server for the Daedalus Knowledge Wiki.

Provides LLM agents with native tool-calling access to the Daedalus
knowledge base from ANY project directory. Zero-dependency on Obsidian CLI;
all operations use pure filesystem analysis.

Tools:
  search     — Full-text search across wiki nodes with relevance scoring
  read       — Read a specific wiki node by name or path
  list_nodes — List all wiki nodes grouped by domain
  backlinks  — Find nodes that link TO a given node
  outlinks   — Find nodes that a given node links TO
  crawl      — Full graph context (content + incoming + outgoing links)
  audit      — Wiki health diagnostics (ghost links, orphans, coverage)
  summary    — Condensed vault overview (domains, hubs, leaves)

Usage:
  # Run directly:
  python daedalus_mcp.py

  # Register with Gemini CLI:
  gemini mcp add daedalus -- /path/to/.mcp_venv/bin/python /path/to/daedalus_mcp.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from fastmcp import FastMCP

# ─── Configuration ──────────────────────────────────────────────────────────

VAULT_DIR = Path(__file__).resolve().parent
WIKI_DIR = VAULT_DIR / "wiki"
SKIP_FILES = {"index.md", "log.md", "Ingestion_Tracker.md"}

# Source reference patterns (raw clipper titles — NOT wiki nodes)
SOURCE_PATTERNS = [
    "Akitando", "Clipper", "Distrobox de Emulação",
    "Blockchains servem", "Introdução a Redes", "Entendendo",
    "Burlando", "Criando uma Rede", "Criptografia", "Protegendo",
    "RANT", "Detecção", "Como Funciona", "Como sua Internet",
    "Sua Segurança", "YouTube",
]

# Portuguese → English term map for bilingual search
# The wiki content is in English but users may query in Portuguese.
# This map enables automatic query expansion.
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


# ─── Core Library ───────────────────────────────────────────────────────────

def _is_source_ref(target: str) -> bool:
    return any(p in target for p in SOURCE_PATTERNS)


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


def _build_registry() -> dict:
    """Build a complete node registry with metadata, outlinks, and backlinks.

    Returns dict: stem -> {path, size, has_frontmatter, tags, links_out, backlinks, domain}
    """
    link_re = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")
    registry = {}

    for md in WIKI_DIR.rglob("*.md"):
        if md.name in SKIP_FILES:
            continue
        stem = md.stem
        rel = str(md.relative_to(VAULT_DIR))
        content = md.read_text(errors="replace")
        size = md.stat().st_size

        # Parse frontmatter
        has_fm = content.startswith("---")
        tags = []
        if has_fm:
            fm_end = content.find("---", 3)
            if fm_end > 0:
                fm = content[3:fm_end]
                m = re.search(r"tags:\s*\[([^\]]+)\]", fm)
                if m:
                    tags = [t.strip() for t in m.group(1).split(",")]

        # Extract outlinks (ignoring source references and heading anchors)
        raw = link_re.findall(content)
        out = []
        for lnk in raw:
            t = lnk.split("#")[0].strip()
            if t and not _is_source_ref(t):
                out.append(t)

        parts = rel.split("/")
        registry[stem] = {
            "path": rel,
            "size": size,
            "has_frontmatter": has_fm,
            "tags": tags,
            "links_out": out,
            "backlinks": [],
            "domain": parts[1] if len(parts) > 2 else "_root",
        }

    # Compute backlinks
    for stem, info in registry.items():
        for t in info["links_out"]:
            ts = t.replace(".md", "").split("/")[-1]
            if ts in registry:
                registry[ts]["backlinks"].append(stem)

    return registry


def _resolve_stem(name: str) -> str:
    """Normalize a node reference to its stem form."""
    return name.replace(".md", "").split("/")[-1]


def _search_wiki(query: str, limit: int = 10) -> list:
    """Pure filesystem full-text search with relevance scoring and PT→EN expansion."""
    expanded = _expand_query(query)
    terms = expanded.lower().split()
    results = []

    for md in WIKI_DIR.rglob("*.md"):
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
                    "file": str(md.relative_to(VAULT_DIR)),
                    "score": score,
                    "matches": unique[:4],
                }
            )

    results.sort(key=lambda x: -x["score"])
    return results[:limit]


# ─── MCP Server ─────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="Daedalus",
    instructions=(
        "Daedalus is a curated technical knowledge wiki covering Computer Science, "
        "Infrastructure & DevOps, Security, Programming, Databases, Operating Systems, "
        "and more (68 synthesis nodes, 203 wikilinks). "
        "Use these tools to research technical topics before answering questions. "
        "Workflow: summary → search → read → crawl for deep context.\n\n"
        "IMPORTANT: Wiki content is written in ENGLISH. The search tool automatically "
        "translates Portuguese terms to English, so queries in either language work. "
        "However, for best results, prefer English search terms when possible."
    ),
)


@mcp.tool()
def search(query: str, limit: int = 5) -> str:
    """Search the Daedalus knowledge wiki by topic.

    Returns ranked results with context snippets. Start here when
    researching a technical concept.

    The search automatically expands Portuguese terms to English
    equivalents, since wiki content is in English.

    Args:
        query: Search terms (e.g. "containers namespaces cgroups")
        limit: Maximum results to return (default 5)
    """
    results = _search_wiki(query, limit)
    if not results:
        return f"No results found for: '{query}'"

    lines = [f"Found {len(results)} result(s) for '{query}':\n"]
    for r in results:
        lines.append(f"📄 {r['file']} (score: {r['score']})")
        for m in r["matches"]:
            lines.append(f"  L{m['line']}: {m['text']}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def read(filepath: str) -> str:
    """Read the full content of a wiki node.

    Args:
        filepath: Relative path (e.g. "wiki/Operating_Systems/Memory_Management.md")
                  or just the node name (e.g. "Memory_Management")
    """
    # Try direct path
    target = VAULT_DIR / filepath
    if target.exists() and target.is_file():
        return target.read_text(errors="replace")

    # Try finding by stem
    stem = _resolve_stem(filepath)
    for md in WIKI_DIR.rglob("*.md"):
        if md.stem == stem:
            return md.read_text(errors="replace")

    return f"❌ Node not found: {filepath}"


@mcp.tool()
def list_nodes() -> str:
    """List all wiki nodes grouped by domain.

    Use this to discover available topics in the knowledge base.
    """
    registry = _build_registry()
    domains = defaultdict(list)
    for stem, info in registry.items():
        domains[info["domain"]].append(stem)

    result = {
        "total_nodes": len(registry),
        "domains": {
            d: sorted(nodes) for d, nodes in sorted(domains.items())
        },
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def backlinks(node_name: str) -> str:
    """Find all nodes that link TO the given node.

    Useful for discovering related context and how concepts connect.

    Args:
        node_name: Node stem (e.g. "Memory_Management") or full path
    """
    stem = _resolve_stem(node_name)
    registry = _build_registry()

    if stem not in registry:
        return f"❌ Node not found: {node_name}"

    bl = registry[stem]["backlinks"]
    if not bl:
        return f"No backlinks for: {stem}"

    result = {
        "node": stem,
        "backlink_count": len(bl),
        "backlinks": [
            {"stem": b, "path": registry[b]["path"]} for b in sorted(bl)
        ],
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def outlinks(node_name: str) -> str:
    """Find all nodes that the given node links TO.

    Args:
        node_name: Node stem (e.g. "Memory_Management") or full path
    """
    stem = _resolve_stem(node_name)
    registry = _build_registry()

    if stem not in registry:
        return f"❌ Node not found: {node_name}"

    out = list(dict.fromkeys(registry[stem]["links_out"]))  # deduplicate
    if not out:
        return f"No outlinks for: {stem}"

    resolved = []
    for o in sorted(out):
        ts = _resolve_stem(o)
        entry = {"target": ts}
        if ts in registry:
            entry["path"] = registry[ts]["path"]
        else:
            entry["status"] = "unresolved"
        resolved.append(entry)

    result = {
        "node": stem,
        "outlink_count": len(resolved),
        "outlinks": resolved,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def crawl(node_name: str) -> str:
    """Full knowledge graph context: content + incoming + outgoing links.

    The most comprehensive view of a node. Use when you need deep
    context about a specific topic.

    Args:
        node_name: Node stem (e.g. "Memory_Management") or path
    """
    stem = _resolve_stem(node_name)
    registry = _build_registry()

    if stem not in registry:
        return f"❌ Node not found: {node_name}"

    info = registry[stem]
    content = (VAULT_DIR / info["path"]).read_text(errors="replace")
    unique_out = list(dict.fromkeys(info["links_out"]))

    sections = [f"═══ {stem} ({info['path']}) ═══"]

    if info["backlinks"]:
        sections.append(f"\n↙ Incoming ({len(info['backlinks'])}):")
        for b in sorted(info["backlinks"]):
            sections.append(f"  ← {b}")

    if unique_out:
        sections.append(f"\n↗ Outgoing ({len(unique_out)}):")
        for o in sorted(unique_out):
            sections.append(f"  → {_resolve_stem(o)}")

    sections.append(f"\n{'─' * 60}\n{content}")
    return "\n".join(sections)


@mcp.tool()
def audit() -> str:
    """Comprehensive wiki health check.

    Returns: ghost links, orphans, missing frontmatter, index coverage,
    connectivity stats, and overall health score.
    """
    registry = _build_registry()
    all_stems = set(registry.keys())

    # Ghost links
    ghosts = defaultdict(list)
    for stem, info in registry.items():
        for t in info["links_out"]:
            ts = _resolve_stem(t)
            if ts not in all_stems:
                ghosts[ts].append(stem)

    # Index coverage & orphans
    idx_path = WIKI_DIR / "index.md"
    idx = idx_path.read_text(errors="replace") if idx_path.exists() else ""
    missing_idx = []
    orphans = []
    for stem in sorted(all_stems):
        display = stem.replace("_", " ")
        in_index = stem in idx or display in idx
        if not in_index:
            missing_idx.append(stem)
        if not registry[stem]["backlinks"] and not in_index:
            orphans.append(stem)

    no_fm = sorted(s for s, i in registry.items() if not i["has_frontmatter"])

    avg_out = round(
        sum(len(i["links_out"]) for i in registry.values()) / max(len(registry), 1), 1
    )
    avg_bl = round(
        sum(len(i["backlinks"]) for i in registry.values()) / max(len(registry), 1), 1
    )

    issues = len(ghosts) + len(orphans) + len(no_fm) + len(missing_idx)

    result = {
        "total_nodes": len(registry),
        "avg_outlinks": avg_out,
        "avg_backlinks": avg_bl,
        "ghost_links": dict(sorted(ghosts.items())),
        "ghost_link_count": len(ghosts),
        "orphan_nodes": sorted(orphans),
        "missing_frontmatter": no_fm,
        "missing_from_index": sorted(missing_idx),
        "health": (
            "EXCELLENT" if issues == 0 else "GOOD" if issues <= 5 else "NEEDS_ATTENTION"
        ),
        "issue_count": issues,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def summary() -> str:
    """Condensed vault overview: domains, hubs, leaves, connectivity.

    Use this FIRST to orient yourself before searching. Returns the
    topology of the knowledge base so you know where to look.
    """
    registry = _build_registry()

    domains = defaultdict(list)
    for stem, info in registry.items():
        domains[info["domain"]].append(stem)

    hubs = []
    leaves = []
    for stem, info in registry.items():
        bl = len(info["backlinks"])
        ol = len(info["links_out"])
        if bl >= 5:
            hubs.append({"node": stem, "backlinks": bl})
        if bl + ol <= 1:
            leaves.append(stem)

    hubs.sort(key=lambda x: -x["backlinks"])

    result = {
        "total_nodes": len(registry),
        "total_wikilinks": sum(len(i["links_out"]) for i in registry.values()),
        "domains": {
            d: {"count": len(n), "nodes": sorted(n)}
            for d, n in sorted(domains.items())
        },
        "hub_nodes": hubs[:15],
        "leaf_nodes": sorted(leaves),
    }
    return json.dumps(result, indent=2)


# ─── Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
