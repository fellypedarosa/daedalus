#!/usr/bin/env python3
"""
daedalus.py — LLM Navigation CLI for the Daedalus Obsidian Wiki.

Usage:
  ./daedalus.py search <query> [--limit N] [--all]
  ./daedalus.py read <filepath>
  ./daedalus.py backlinks <filepath>
  ./daedalus.py crawl <filepath>

By default, search is scoped to wiki/ only. Pass --all to include raw sources.
  ./daedalus.py audit [--format json]
  ./daedalus.py summary [--format json]
"""

import argparse
import subprocess
import json
import os
import re
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

WIKI_PATH = "wiki"
SKIP_FILES = {"index.md", "log.md", "Ingestion_Tracker.md"}

# Known source reference patterns (raw clipper titles, not wiki nodes)
SOURCE_PATTERNS = [
    "Akitando", "Clipper", "Distrobox de Emulação",
    "Blockchains servem", "Introdução a Redes", "Entendendo",
    "Burlando", "Criando uma Rede", "Criptografia", "Protegendo",
    "RANT", "Detecção", "Como Funciona", "Como sua Internet",
    "Sua Segurança", "YouTube"
]

def run_obsidian(args: list) -> str:
    """Executes an obsidian CLI command and returns raw stdout string."""
    try:
        result = subprocess.run(
            ["obsidian"] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] obsidian CLI failed:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

def run_json(args: list) -> list | dict | str:
    """Runs an obsidian CLI command, parses JSON output."""
    raw = run_obsidian(args)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw

# ─────────────────────────────────────────────────────────────────── SEARCH ──

def cmd_search(query: str, limit: int, include_all: bool):
    """
    Contextual search returning deduplicated matches with their containing lines.
    Scoped to wiki/ by default.
    """
    path_flag = []
    if not include_all:
        path_flag = [f"path={WIKI_PATH}"]

    cmd = ["search:context", f"query={query}", f"limit={limit}", "format=json"] + path_flag
    data = run_json(cmd)

    if not data:
        print(f"❌  No results for: '{query}'")
        return

    print(f"\n🔍  '{query}' — {len(data)} file(s) matched\n{'─'*60}")

    for item in data:
        filepath = item.get("file", "?")
        matches = item.get("matches", [])
        
        # Deduplicate identical text on the same line
        seen = set()
        unique_matches = []
        for m in matches:
            key = (m.get("line"), m.get("text", "").strip())
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)

        print(f"\n📄  {filepath}")
        for m in unique_matches:
            line_num = m.get("line", "?")
            text = m.get("text", "").strip()
            # Wrap long lines for legibility
            wrapped = textwrap.fill(text, width=90, initial_indent="     ", subsequent_indent="     ")
            print(f"  L{line_num}:\n{wrapped}")

# ──────────────────────────────────────────────────────────────────── READ ───

def cmd_read(filepath: str):
    """Reads the contents of a specific wiki file and prints it."""
    data = run_json(["read", f"path={filepath}"])
    if not data:
        print(f"❌  Could not read: {filepath}")
        return
    print(f"\n📖  {filepath}\n{'─'*60}\n{data}")

# ─────────────────────────────────────────────────────────────────── LINKS ───

def cmd_backlinks(filepath: str):
    """Lists all files that link TO the given file."""
    raw = run_obsidian(["backlinks", f"path={filepath}", "format=json"])
    if not raw:
        print(f"❌  No backlinks found for: {filepath}")
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = [line.strip() for line in raw.splitlines() if line.strip()]

    if not data:
        print(f"❌  No backlinks found for: {filepath}")
        return

    print(f"\n🔗  Backlinks → {filepath}\n{chr(9472)*60}")
    for item in data:
        link = item if isinstance(item, str) else item.get('file', '?')
        print(f"  ← [[{link}]]")

def cmd_outlinks(filepath: str):
    """Lists all files that the given file links TO."""
    # obsidian links returns a list of strings (file paths), not dicts
    raw = run_obsidian(["links", f"path={filepath}", "format=json"])
    if not raw:
        print(f"❌  No outgoing links found for: {filepath}")
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: split newline-separated text
        data = [line.strip() for line in raw.splitlines() if line.strip()]

    print(f"\n🔗  Outlinks from {filepath}\n{'─'*60}")
    for item in data:
        link = item if isinstance(item, str) else item.get('file', '?')
        print(f"  → [[{link}]]")

# ─────────────────────────────────────────────────────────────────── CRAWL ───

def cmd_crawl(filepath: str):
    """
    Crawl the knowledge graph from a given node: reads the file,
    then lists all backlinks and outgoing links as a graph summary.
    """
    print(f"\n🕸️   Knowledge Graph for: {filepath}\n{'═'*60}")

    # 1. Show incoming links
    backlinks = run_json(["backlinks", f"path={filepath}", "format=json"])
    if backlinks:
        print(f"\n  ↙  Incoming ({len(backlinks)}):")
        for item in backlinks:
            print(f"     ← [[{item.get('file', '?')}]]")
    else:
        print("  ↙  No backlinks.")

    # 2. Show outgoing links
    raw_links = run_obsidian(["links", f"path={filepath}", "format=json"])
    try:
        outlinks = json.loads(raw_links) if raw_links else []
    except json.JSONDecodeError:
        outlinks = [l.strip() for l in raw_links.splitlines() if l.strip()]
    if outlinks:
        print(f"\n  ↗  Outgoing ({len(outlinks)}):")
        for item in outlinks:
            link = item if isinstance(item, str) else item.get('file', '?')
            print(f"     → [[{link}]]")
    else:
        print("  ↗  No outlinks.")

    # 3. Read the file content (summary view)
    print(f"\n{'─'*60}")
    print(f"📖  File contents:\n")
    content = run_json(["read", f"path={filepath}"])
    if content:
        print(content)
    else:
        print("  (empty or unreadable)")

# ─────────────────────────────────────────────────────────────────── AUDIT ───

def _get_base_dir() -> Path:
    """Returns the vault base directory (where daedalus.py lives)."""
    return Path(__file__).resolve().parent

def _build_node_registry() -> dict:
    """Build a registry: stem -> {path, size, has_frontmatter, tags, links_out, backlinks}."""
    base = _get_base_dir()
    wiki = base / WIKI_PATH
    link_re = re.compile(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]')
    registry = {}

    for md_file in wiki.rglob("*.md"):
        if md_file.name in SKIP_FILES:
            continue
        stem = md_file.stem
        rel = str(md_file.relative_to(base))
        content = md_file.read_text(errors="replace")
        size = md_file.stat().st_size

        has_fm = content.startswith("---")
        tags = []
        if has_fm:
            fm_end = content.find("---", 3)
            if fm_end > 0:
                fm_block = content[3:fm_end]
                tag_match = re.search(r'tags:\s*\[([^\]]+)\]', fm_block)
                if tag_match:
                    tags = [t.strip() for t in tag_match.group(1).split(",")]

        # Extract outgoing wikilinks
        raw_links = link_re.findall(content)
        out_links = []
        for lnk in raw_links:
            target = lnk.split("#")[0].strip()  # remove heading anchors
            if not any(p in target for p in SOURCE_PATTERNS):
                out_links.append(target)

        registry[stem] = {
            "path": rel,
            "size": size,
            "has_frontmatter": has_fm,
            "tags": tags,
            "links_out": out_links,
            "backlinks": [],
        }

    # Compute backlinks
    for stem, info in registry.items():
        for target in info["links_out"]:
            # Normalize: target could be "Name_With_Underscore" or path like "Domain/File"
            target_stem = target.replace(".md", "").split("/")[-1]
            if target_stem in registry:
                registry[target_stem]["backlinks"].append(stem)

    return registry


def cmd_audit(fmt: str = "text"):
    """Comprehensive wiki health audit: ghost links, orphans, missing frontmatter, index gaps."""
    base = _get_base_dir()
    registry = _build_node_registry()
    all_stems = set(registry.keys())

    # 1. Ghost links
    ghost_links = defaultdict(list)
    for stem, info in registry.items():
        for target in info["links_out"]:
            target_stem = target.replace(".md", "").split("/")[-1]
            if target_stem not in all_stems:
                ghost_links[target_stem].append(stem)

    # 2. Orphans (no backlinks AND not in index)
    index_path = base / WIKI_PATH / "index.md"
    index_content = index_path.read_text(errors="replace") if index_path.exists() else ""
    orphans = []
    for stem, info in registry.items():
        if not info["backlinks"]:
            display = stem.replace("_", " ")
            if stem not in index_content and display not in index_content:
                orphans.append(stem)

    # 3. Missing frontmatter
    no_frontmatter = [s for s, i in registry.items() if not i["has_frontmatter"]]

    # 4. Index coverage
    missing_from_index = []
    for stem in sorted(all_stems):
        display = stem.replace("_", " ")
        if stem not in index_content and display not in index_content:
            missing_from_index.append(stem)

    # 5. Thin nodes
    thin_nodes = [(s, i["size"]) for s, i in registry.items() if i["size"] < 1500]

    # 6. Connectivity stats
    avg_outlinks = sum(len(i["links_out"]) for i in registry.values()) / max(len(registry), 1)
    avg_backlinks = sum(len(i["backlinks"]) for i in registry.values()) / max(len(registry), 1)

    results = {
        "total_nodes": len(registry),
        "ghost_links": {k: v for k, v in sorted(ghost_links.items())},
        "ghost_link_count": len(ghost_links),
        "orphan_nodes": sorted(orphans),
        "orphan_count": len(orphans),
        "missing_frontmatter": sorted(no_frontmatter),
        "missing_from_index": sorted(missing_from_index),
        "thin_nodes": sorted(thin_nodes, key=lambda x: x[1]),
        "avg_outlinks": round(avg_outlinks, 1),
        "avg_backlinks": round(avg_backlinks, 1),
    }

    if fmt == "json":
        print(json.dumps(results, indent=2))
        return

    # Human-readable output
    print(f"\n🔬  Daedalus Wiki Audit\n{'═'*60}")
    print(f"   Total Nodes: {results['total_nodes']}")
    print(f"   Avg Outlinks: {results['avg_outlinks']} | Avg Backlinks: {results['avg_backlinks']}")

    if results["ghost_links"]:
        print(f"\n❌  Ghost Links ({results['ghost_link_count']}):")
        for target, sources in results["ghost_links"].items():
            print(f"     [[{target}]] ← {', '.join(sources)}")
    else:
        print(f"\n✅  No ghost links found.")

    if results["orphan_nodes"]:
        print(f"\n🏚️   Orphan Nodes ({results['orphan_count']}):")
        for o in results["orphan_nodes"]:
            print(f"     {o}")
    else:
        print(f"\n✅  No orphan nodes.")

    if results["missing_frontmatter"]:
        print(f"\n⚠️   Missing Frontmatter ({len(results['missing_frontmatter'])}):")
        for m in results["missing_frontmatter"]:
            print(f"     {m}")

    if results["missing_from_index"]:
        print(f"\n📋  Missing from Index ({len(results['missing_from_index'])}):")
        for m in results["missing_from_index"]:
            print(f"     {m}")

    if results["thin_nodes"]:
        print(f"\n📝  Thin Nodes < 1.5KB ({len(results['thin_nodes'])}):")
        for name, size in results["thin_nodes"]:
            print(f"     {name} ({size}B)")

    # Overall health score
    issues = results["ghost_link_count"] + results["orphan_count"] + len(results["missing_frontmatter"]) + len(results["missing_from_index"])
    if issues == 0:
        print(f"\n🏆  Health: EXCELLENT — No critical issues.")
    elif issues <= 5:
        print(f"\n✅  Health: GOOD — {issues} minor issue(s).")
    else:
        print(f"\n⚠️   Health: NEEDS ATTENTION — {issues} issue(s) found.")


def cmd_summary(fmt: str = "text"):
    """Condensed vault metadata: nodes per domain, hubs, leaves."""
    registry = _build_node_registry()

    # Group by domain
    domains = defaultdict(list)
    for stem, info in registry.items():
        parts = info["path"].split("/")
        domain = parts[1] if len(parts) > 2 else "_root"
        domains[domain].append(stem)

    # Identify hubs (>= 5 backlinks) and leaves (<= 1 total links)
    hubs = []
    leaves = []
    for stem, info in registry.items():
        bl_count = len(info["backlinks"])
        ol_count = len(info["links_out"])
        if bl_count >= 5:
            hubs.append((stem, bl_count))
        if bl_count + ol_count <= 1:
            leaves.append(stem)

    hubs.sort(key=lambda x: -x[1])

    results = {
        "total_nodes": len(registry),
        "domains": {d: {"count": len(nodes), "nodes": sorted(nodes)} for d, nodes in sorted(domains.items())},
        "hub_nodes": hubs[:15],
        "leaf_nodes": sorted(leaves),
        "total_wikilinks": sum(len(i["links_out"]) for i in registry.values()),
    }

    if fmt == "json":
        print(json.dumps(results, indent=2))
        return

    # Human-readable output
    print(f"\n📊  Daedalus Wiki Summary\n{'═'*60}")
    print(f"   Total Nodes: {results['total_nodes']}")
    print(f"   Total Wikilinks: {results['total_wikilinks']}")

    print(f"\n📁  Domains:")
    for domain, info in results["domains"].items():
        print(f"     {domain}: {info['count']} nodes")

    if hubs:
        print(f"\n🌟  Hub Nodes (≥5 backlinks):")
        for name, count in hubs:
            print(f"     {name} ({count} backlinks)")

    if leaves:
        print(f"\n🍂  Leaf Nodes (≤1 total link): {len(leaves)}")
        for name in leaves[:10]:
            print(f"     {name}")
        if len(leaves) > 10:
            print(f"     ... and {len(leaves) - 10} more")


# ────────────────────────────────────────────────────────────────── ENTRY ────

def main():
    parser = argparse.ArgumentParser(
        prog="daedalus",
        description="LLM Navigation wrapper for the Daedalus Obsidian Wiki.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              ./daedalus.py search "cgroups e namespaces"
              ./daedalus.py search "TCP handshake" --all
              ./daedalus.py read wiki/Infrastructure_and_DevOps/Virtualization_and_High_Performance_Systems.md
              ./daedalus.py backlinks wiki/Databases/Database_Fundamentals.md
              ./daedalus.py crawl wiki/Computer_Science/Compiler_Design.md
              ./daedalus.py audit
              ./daedalus.py audit --format json
              ./daedalus.py summary --format json
        """),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search", help="Contextual full-text search (wiki/ only by default)")
    p_search.add_argument("query", help="Search query string")
    p_search.add_argument("--limit", type=int, default=10, help="Max files to return (default: 10)")
    p_search.add_argument("--all", action="store_true", dest="include_all", help="Include raw/ sources in search")

    # read
    p_read = subparsers.add_parser("read", help="Read a wiki file")
    p_read.add_argument("filepath", help="Relative vault path (e.g. wiki/Folder/File.md)")

    # backlinks
    p_bl = subparsers.add_parser("backlinks", help="Find files that link TO a given note")
    p_bl.add_argument("filepath", help="Relative vault path")

    # outlinks
    p_ol = subparsers.add_parser("outlinks", help="Find links FROM a given note")
    p_ol.add_argument("filepath", help="Relative vault path")

    # crawl
    p_cr = subparsers.add_parser("crawl", help="Full graph crawl of a node (backlinks + outlinks + content)")
    p_cr.add_argument("filepath", help="Relative vault path")

    # audit
    p_audit = subparsers.add_parser("audit", help="Wiki health audit (ghost links, orphans, coverage)")
    p_audit.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    # summary
    p_summary = subparsers.add_parser("summary", help="Condensed vault overview (domains, hubs, leaves)")
    p_summary.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args.query, args.limit, args.include_all)
    elif args.command == "read":
        cmd_read(args.filepath)
    elif args.command == "backlinks":
        cmd_backlinks(args.filepath)
    elif args.command == "outlinks":
        cmd_outlinks(args.filepath)
    elif args.command == "crawl":
        cmd_crawl(args.filepath)
    elif args.command == "audit":
        cmd_audit(args.format)
    elif args.command == "summary":
        cmd_summary(args.format)


if __name__ == "__main__":
    main()
