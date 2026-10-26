#!/usr/bin/env python3
"""Build an auxiliary knowledge index without editing its source Markdown."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from daedalus_paths import vault_dir
from daedalus_search.engine import SearchEngine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=vault_dir())
    parser.add_argument("--index-dir", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--max-tokens", type=int, default=int(os.environ.get("DAEDALUS_PASSAGE_TOKENS", "256")))
    parser.add_argument("--lexical-only", action="store_true")
    args = parser.parse_args()
    engine = SearchEngine(args.vault, args.index_dir or os.environ.get("DAEDALUS_INDEX_DIR"),
                          model_dir=args.model_dir or os.environ.get("DAEDALUS_MODEL_DIR"),
                          max_tokens=args.max_tokens, interval=0)
    try:
        result = engine.reindex(semantic=not args.lexical_only)
        print(json.dumps(result, indent=2))
        if args.model_dir and not engine.encoder:
            raise SystemExit("Requested semantic model unavailable; lexical generation remains usable")
    finally:
        engine.close()


if __name__ == "__main__":
    main()
