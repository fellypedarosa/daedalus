"""Rank fusion and evidence selection, without changing source text."""
from __future__ import annotations

from .lexical import query_terms
from .models import Candidate


def fuse(*rankings: list[Candidate], constant: int = 60) -> list[Candidate]:
    result: dict[str, Candidate] = {}
    for ranking in rankings:
        seen = set()
        for rank, candidate in enumerate(ranking, 1):
            pid = candidate.passage.id
            if pid in seen:
                continue
            seen.add(pid)
            current = result.setdefault(pid, Candidate(candidate.passage))
            current.score += 1.0 / (constant + rank)
            current.channels.update(candidate.channels)
            current.via.extend(v for v in candidate.via if v not in current.via)
    return sorted(result.values(), key=lambda c: (-c.score, c.passage.id))


def select(candidates, documents, limit, themes=False, per_document=2):
    offset = -min(0.0, min((c.score for c in candidates), default=0.0))
    groups: dict[str, list[Candidate]] = {}
    texts = set()
    for candidate in candidates:
        passage = candidate.passage
        fingerprint = " ".join(passage.text.casefold().split())
        if fingerprint in texts:
            continue
        group = groups.setdefault(passage.path, [])
        if len(group) < per_document:
            # Overlapping source ranges are not independent evidence.
            if not any(max(passage.start_offset, c.passage.start_offset) <
                       min(passage.end_offset, c.passage.end_offset) for c in group):
                group.append(candidate)
                texts.add(fingerprint)
    remaining = {path: items for path, items in groups.items() if items}
    selected, domains, tags, origins = [], set(), set(), set()
    while remaining and len(selected) < limit:
        def priority(path):
            doc = documents[path]
            score = remaining[path][0].score + offset
            if themes:
                novelty = int(doc.domain not in domains) + int(bool(set(doc.tags) - tags))
                score *= 1 + .15 * novelty
            # Avoid over-counting a synthesis and its source, while allowing both
            # when they really contain complementary evidence.
            sources = {r.target for r in doc.relations if r.kind == "source" and r.target}
            if path in origins or sources.intersection(origins):
                score *= .9
            return score
        path = min(remaining, key=lambda p: (-priority(p), p))
        items = remaining.pop(path)
        selected.append((documents[path], items))
        domains.add(documents[path].domain)
        tags.update(documents[path].tags)
        origins.add(path)
        origins.update(r.target for r in documents[path].relations if r.kind == "source" and r.target)
    return selected
