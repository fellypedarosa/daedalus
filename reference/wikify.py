#!/usr/bin/env python3
"""
wikify.py — Automated wikilink injector for the Daedalus Wiki.

Scans all wiki nodes for mentions of other node titles (or aliases)
and injects [[wikilinks]] where plain text references exist.

Usage: python3 wikify.py [--dry-run]
"""

import os
import re
import sys

WIKI_DIR = "wiki"
SKIP_FILES = {"index.md", "log.md", "Ingestion_Tracker.md"}

# Build a map: display_name -> filename_stem
# e.g. "Memory Management" -> "Memory_Management"
def build_node_map():
    nodes = {}
    for root, dirs, files in os.walk(WIKI_DIR):
        for f in files:
            if f in SKIP_FILES or not f.endswith(".md"):
                continue
            stem = f.replace(".md", "")
            # Convert filename stem to display name
            display = stem.replace("_", " ")
            nodes[display] = stem
            # Also add common short aliases
            # e.g. "OSI and TCPIP Models" -> also match "OSI"
    return nodes

def wikify_file(filepath, node_map, own_stem, dry_run=False):
    """Inject [[wikilinks]] into a file for mentions of other node names."""
    with open(filepath, "r") as f:
        content = f.read()
    
    original = content
    changes = 0
    
    for display_name, stem in sorted(node_map.items(), key=lambda x: -len(x[0])):
        # Don't self-link
        if stem == own_stem:
            continue
        
        # Skip very short names that would cause false positives
        if len(display_name) < 6:
            continue
        
        # Pattern: find the display name NOT already inside a [[...]] or a link
        # Match whole words only, case insensitive
        pattern = re.compile(
            r'(?<!\[\[)'           # not preceded by [[
            r'(?<!\|)'             # not preceded by | (inside wikilink)
            r'\b(' + re.escape(display_name) + r')\b'
            r'(?!\]\])'           # not followed by ]]
            r'(?!\|)'             # not followed by | (inside wikilink)
            r'(?![^\[]*\]\])',    # not inside an existing [[...]]
            re.IGNORECASE
        )
        
        # Only replace the FIRST occurrence to avoid over-linking
        match = pattern.search(content)
        if match:
            # Check this isn't inside frontmatter (between --- lines)
            before = content[:match.start()]
            dashes = before.count("---")
            if dashes >= 2:  # Past frontmatter
                replacement = f"[[{stem}|{match.group(1)}]]"
                content = content[:match.start()] + replacement + content[match.end():]
                changes += 1
    
    if changes > 0 and not dry_run:
        with open(filepath, "w") as f:
            f.write(content)
    
    return changes

def main():
    dry_run = "--dry-run" in sys.argv
    node_map = build_node_map()
    
    print(f"📚 Found {len(node_map)} wiki nodes")
    if dry_run:
        print("🔍 DRY RUN — no files will be modified\n")
    
    total_changes = 0
    files_changed = 0
    
    for root, dirs, files in os.walk(WIKI_DIR):
        for f in files:
            if f in SKIP_FILES or not f.endswith(".md"):
                continue
            filepath = os.path.join(root, f)
            own_stem = f.replace(".md", "")
            changes = wikify_file(filepath, node_map, own_stem, dry_run)
            if changes > 0:
                files_changed += 1
                total_changes += changes
                print(f"  {'🔗' if not dry_run else '👁️'} {filepath}: +{changes} links")
    
    print(f"\n{'✅ Applied' if not dry_run else '👁️ Would apply'}: {total_changes} new links across {files_changed} files")

if __name__ == "__main__":
    main()
