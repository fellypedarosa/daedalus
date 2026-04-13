#!/usr/bin/env python3
"""
fix_ghosts.py — Resolves ghost wikilinks caused by space/underscore
mismatch and other common issues in the Daedalus Wiki.

Obsidian resolves [[Name With Spaces]] to Name_With_Spaces.md via fuzzy
matching, but raw markdown consumers (LLM agents) cannot. This script
normalizes all wikilinks to use explicit stem|alias format.

Usage:
  python3 fix_ghosts.py [--dry-run]
"""

import os
import re
import sys

WIKI_DIR = "wiki"
SKIP_FILES = {"index.md", "log.md", "Ingestion_Tracker.md"}

# Known source references that should NOT be normalized (raw clipper titles)
SOURCE_PATTERNS = [
    "Akitando", "Clipper", "Distrobox de Emulação",
    "Blockchains servem", "Introdução a Redes", "Entendendo",
    "Burlando", "Criando uma Rede", "Criptografia", "Protegendo",
    "RANT", "Detecção", "Como Funciona", "Como sua Internet",
    "Sua Segurança", "YouTube"
]


def is_source_reference(target: str) -> bool:
    """Check if a wikilink target is a raw source reference (not a wiki node)."""
    return any(p in target for p in SOURCE_PATTERNS)


def build_stem_set() -> dict:
    """Build a mapping from file stem (e.g. 'Memory_Management') to its relative path."""
    stems = {}
    for root, dirs, files in os.walk(WIKI_DIR):
        for f in files:
            if f in SKIP_FILES or not f.endswith(".md"):
                continue
            stem = f.replace(".md", "")
            rel = os.path.relpath(os.path.join(root, f), WIKI_DIR)
            stems[stem] = rel
    return stems


def normalize_link(match: re.Match, stems: dict) -> str:
    """Normalize a single wikilink match."""
    full = match.group(0)  # e.g. [[Name With Spaces]]
    inner = match.group(1)  # e.g. Name With Spaces

    # Already has alias — check if stem part resolves
    if "|" in inner:
        target, alias = inner.split("|", 1)
        target = target.strip()
        alias = alias.strip()
        # If target has heading anchor, split it
        heading = ""
        if "#" in target:
            target, heading = target.split("#", 1)
            heading = "#" + heading
        # Check if target needs underscore fix
        underscore_target = target.replace(" ", "_")
        if target not in stems and underscore_target in stems:
            return f"[[{underscore_target}{heading}|{alias}]]"
        return full

    # No alias — plain [[Target]] or [[Target#Heading]]
    target = inner.strip()
    heading = ""
    if "#" in target:
        target, heading = target.split("#", 1)
        heading_text = heading
        heading = "#" + heading

    # Skip source references
    if is_source_reference(target):
        return full

    # Try underscore normalization
    underscore_target = target.replace(" ", "_")

    if target in stems:
        # Already resolves — no change needed
        return full
    elif underscore_target in stems:
        # Space→underscore fixes it
        if heading:
            return f"[[{underscore_target}{heading}|{target}]]"
        else:
            return f"[[{underscore_target}|{target}]]"
    else:
        # Still unresolved — leave as-is (might be heading-only ref or future node)
        return full


def fix_file(filepath: str, stems: dict, dry_run: bool = False) -> int:
    """Fix all wikilinks in a single file. Returns number of changes."""
    with open(filepath, "r") as f:
        content = f.read()

    original = content

    # Match all wikilinks: [[...]]
    pattern = re.compile(r'\[\[([^\]]+)\]\]')

    new_content = pattern.sub(lambda m: normalize_link(m, stems), content)

    if new_content == original:
        return 0

    # Count changes
    changes = sum(1 for a, b in zip(
        pattern.findall(original), pattern.findall(new_content)
    ) if a != b)

    if not dry_run:
        with open(filepath, "w") as f:
            f.write(new_content)

    return changes


def main():
    dry_run = "--dry-run" in sys.argv
    stems = build_stem_set()

    print(f"📚 Found {len(stems)} wiki nodes")
    if dry_run:
        print("🔍 DRY RUN — no files will be modified\n")

    total_changes = 0
    files_changed = 0

    for root, dirs, files in os.walk(WIKI_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue
            filepath = os.path.join(root, f)
            changes = fix_file(filepath, stems, dry_run)
            if changes > 0:
                files_changed += 1
                total_changes += changes
                print(f"  {'✅' if not dry_run else '👁️'} {filepath}: {changes} link(s) fixed")

    print(f"\n{'✅ Applied' if not dry_run else '👁️ Would apply'}: "
          f"{total_changes} fixes across {files_changed} files")


if __name__ == "__main__":
    main()
