#!/usr/bin/env python3
"""Evaluate retrieval on an explicit corpus; never write knowledge files."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from daedalus_paths import vault_dir


def implementation_manifest():
    root = Path(__file__).resolve().parents[1]
    paths = [*sorted((root / "daedalus_search").glob("*.py")), root / "daedalus_mcp.py",
             root / "daedalus_paths.py", Path(__file__).resolve(), root / "requirements.lock"]
    baseline = root / "tests/evaluation/legacy.py"
    if baseline.exists():
        paths.append(baseline)
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


IMPLEMENTATION_AT_START = implementation_manifest()

from daedalus_search.documents import scan_paths, stable_read
from daedalus_search.engine import SearchEngine
from daedalus_search.models import digest


def metrics(paths, judgments, k=5):
    paths = paths[:k]
    relevant = {p for p, grade in judgments.items() if grade > 0}
    grades = [judgments.get(path, 0) for path in paths]
    dcg = sum((2 ** grade - 1) / math.log2(i + 2) for i, grade in enumerate(grades))
    ideal = sum((2 ** grade - 1) / math.log2(i + 2) for i, grade in
                enumerate(sorted(judgments.values(), reverse=True)[:k]))
    return {"ndcg_at_5": dcg / ideal if ideal else None,
            "mrr_at_5": next((1 / (i + 1) for i, g in enumerate(grades) if g > 0), 0) if relevant else None,
            "recall_at_5": len(set(paths) & relevant) / len(relevant) if relevant else None,
            "precision_at_5": sum(g > 0 for g in grades) / k,
            "returned_documents": len(paths)}


def aggregate(records):
    result = {}
    for key in ("ndcg_at_5", "mrr_at_5", "recall_at_5", "precision_at_5", "returned_documents"):
        values = [r["metrics"][key] for r in records if r["metrics"][key] is not None]
        result[key] = statistics.mean(values) if values else None
    times = sorted(r["elapsed_ms"] for r in records)
    result["latency_p50_ms"] = statistics.median(times) if times else None
    result["latency_p95_ms"] = times[max(0, math.ceil(len(times) * .95) - 1)] if times else None
    result["query_count"] = len(records)
    return result


def manifest(root):
    return {path: digest(stable_read(root, path)[0]) for path in scan_paths(root)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=vault_dir())
    parser.add_argument("--queries", type=Path, default=Path(__file__).resolve().parents[1] / "tests/evaluation/queries.json")
    parser.add_argument("--backend", choices=["legacy", "lexical", "hybrid", "graph", "rerank"], default="lexical")
    parser.add_argument("--index-dir", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--reranker-dir", type=Path)
    parser.add_argument("--split", choices=["tuning", "validation", "all"], default="validation")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()
    args.vault = args.vault.resolve()
    dataset_bytes = args.queries.read_bytes()
    dataset = json.loads(dataset_bytes)
    if args.backend == "legacy":
        from tests.evaluation.legacy import search as legacy_search
    queries = [q for q in dataset["queries"] if args.split == "all" or q["split"] == args.split]
    before = manifest(args.vault)
    engine, build = None, None
    try:
        if args.backend != "legacy":
            if args.backend != "lexical" and not args.model_dir:
                raise SystemExit("Semantic evaluation requires --model-dir; lexical fallback cannot be scored as hybrid")
            engine = SearchEngine(args.vault, args.index_dir, model_dir=args.model_dir,
                reranker_dir=args.reranker_dir if args.backend == "rerank" else None,
                interval=0, max_tokens=args.max_tokens,
                enable_graph=args.backend in {"graph", "rerank"})
            build = engine.reindex(semantic=args.backend != "lexical")
            if args.backend != "lexical" and not engine.status()["retrieval"] == "hybrid":
                raise SystemExit("Requested model unavailable; refusing to label lexical results as hybrid")
        records, citations, correct = [], 0, 0
        for q in queries:
            missing = [p for p in q["judgments"] if p not in before]
            if missing:
                raise SystemExit("Evaluation corpus is missing judged documents: " + ", ".join(missing))
            started = time.perf_counter()
            if engine:
                result = engine.search(q["query"], scope=q.get("scope", "wiki"), mode=q.get("mode", "auto"))
                paths = [r["path"] for r in result["results"]]
                for entry in result["results"]:
                    data, text = stable_read(args.vault, entry["path"])
                    for p in entry["passages"]:
                        citations += 1
                        correct += int(digest(data) == entry["document_hash"] and
                            text[p["start_offset"]:p["end_offset"]] == p["text"] and
                            p["start_line"] == text.count("\n", 0, p["start_offset"]) + 1)
                warnings = result["warnings"]
                chars = sum(len(p["text"]) for r in result["results"] for p in r["passages"])
            else:
                # Preserve the old wiki-only contract. Raw/all evaluations are
                # identified separately rather than pretending equal coverage.
                paths = [r["file"] for r in legacy_search(args.vault, q["query"], 5)]
                warnings, chars = [], None
            records.append({"id": q["id"], "category": q["category"], "query": q["query"],
                "scope": q.get("scope", "wiki"), "expected": q["judgments"], "paths": paths,
                "metrics": metrics(paths, q["judgments"]), "warnings": warnings,
                "context_characters": chars, "elapsed_ms": (time.perf_counter() - started) * 1000})
        after = manifest(args.vault)
        if after != before:
            raise SystemExit("Knowledge changed during evaluation; report is not comparable")
        git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        report = {"schema_version": 1, "backend": args.backend, "split": args.split,
            "judgment_status": dataset.get("judgment_status", "unreviewed"), "commit": git.stdout.strip(),
            "corpus": before, "corpus_hash": digest(json.dumps(before, sort_keys=True)),
            "notes_unchanged": True, "build": build, "configuration": {
                "max_tokens": args.max_tokens, "graph": args.backend in {"graph", "rerank"},
                "effective_passage_tokens": min(args.max_tokens, engine.encoder.max_length - 48) if engine and engine.encoder else args.max_tokens,
                "model": engine.encoder.spec if engine and engine.encoder else None},
            "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            "citation_accuracy": correct / citations if citations else None,
            "metrics": aggregate(records), "by_category": {category: aggregate([r for r in records if r["category"] == category])
                for category in sorted({r["category"] for r in records})}, "queries": records}
        if implementation_manifest() != IMPLEMENTATION_AT_START or args.queries.read_bytes() != dataset_bytes:
            raise SystemExit("Implementation or evaluation dataset changed during the run; report rejected")
        report["implementation_manifest"] = IMPLEMENTATION_AT_START
        report["dataset_hash"] = digest(dataset_bytes)
        report["environment"] = {"python": platform.python_version(), "platform": platform.platform(),
            "cpu_count": os.cpu_count(), "openblas_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
            "onnx_intraop_threads": 2 if engine and engine.encoder else None}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({k: report[k] for k in ("backend", "judgment_status", "metrics", "citation_accuracy", "peak_rss_mib")}, indent=2))
    finally:
        if engine:
            engine.close()


if __name__ == "__main__":
    main()
