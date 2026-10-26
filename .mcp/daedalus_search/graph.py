"""One-hop, provenance-preserving expansion; authorship never boosts topics."""
from __future__ import annotations

from .lexical import lexical_search


def expand(candidates, documents, connection, passages, query, scope, semantic=None,
           seeds=5, budget=20):
    roots = list(dict.fromkeys(c.passage.path for c in candidates))[:seeds]
    neighbors: dict[str, list[dict]] = {}
    for source, doc in documents.items():
        for relation in doc.relations:
            if not relation.target or relation.kind not in {"topic", "source"}:
                continue
            if source in roots:
                target, origin = relation.target, source
            elif relation.target in roots:
                target, origin = source, relation.target
            else:
                continue
            if target in roots or (scope != "all" and not target.startswith(scope + "/")):
                continue
            neighbors.setdefault(target, []).append({"from": origin, "to": target,
                "relation": relation.kind, "reference_document": source, "line": relation.line})
    # Bound fanout BEFORE searching, not after loading a high-degree hub.
    paths = set(sorted(neighbors)[:20])
    found = lexical_search(connection, query, passages, scope, budget, paths)
    if semantic and paths:
        from .ranking import fuse
        found = fuse(found, semantic.search(query, passages, scope, budget, paths))[:budget]
    for candidate in found:
        candidate.channels.add("graph")
        candidate.via = neighbors[candidate.passage.path]
    return found[:budget]
