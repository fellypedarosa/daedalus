"""Safe lexical queries: technical symbols retain a literal retrieval channel."""
from __future__ import annotations

import re
from .documents import normalized
from .models import Candidate, Passage, digest

STOPWORDS = set("""a o as os e de da do das dos em na no nas nos um uma uns umas
para por com sem que como qual quais quando onde quem entre sobre ao aos se sua seu
suas seus esta este isso isto quais sao ser foi dos das uma the a an and or of to in
on for with without what which how when where is are be this that these those does
do can i my me it its than from at by not after before using use""".split())


def query_terms(query: str) -> list[str]:
    # FTS unicode61 splits underscores and punctuation. Keep technical originals
    # separately for literal checks rather than interpolating them into MATCH.
    tokens = re.findall(r"[^\W_]+", normalized(query), re.UNICODE)
    return list(dict.fromkeys(t for t in tokens if t not in STOPWORDS))[:48]


def literal_terms(query: str) -> list[str]:
    quoted = re.findall(r'"([^"\n]+)"', query)
    technical = re.findall(r"(?<!\w)(?:[A-Za-z][\w.-]*\+\+|\.[A-Za-z][\w.-]*|--[\w-]+|\w*[A-Z]\w*\d\w*|\d+(?:\.\d+)+)(?!\w)", query)
    return list(dict.fromkeys(quoted + technical))[:16]


def expression(query: str) -> str:
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in query_terms(query))


def lexical_search(connection, query: str, passages: dict, scope: str = "all",
                   limit: int = 30, paths: set[str] | None = None) -> list[Candidate]:
    match = expression(query)
    if not match:
        return []
    clauses, parameters = ["passages_fts MATCH ?"], [match]
    if scope != "all":
        clauses.append("p.path LIKE ?")
        parameters.append(scope + "/%")
    if paths is not None:
        if not paths:
            return []
        clauses.append("p.path IN (" + ",".join("?" for _ in paths) + ")")
        parameters.extend(sorted(paths))
    sql = ("SELECT p.id, bm25(passages_fts, 6.0, 5.0, 3.0, 1.0) AS rank "
           "FROM passages_fts JOIN passages p ON p.rowid=passages_fts.rowid WHERE "
           + " AND ".join(clauses) + " ORDER BY rank, p.id LIMIT ?")
    rows = connection.execute(sql, [*parameters, limit]).fetchall()
    return [Candidate(passages[row["id"]], -row["rank"], {"lexical"}) for row in rows]


def literal_search(passages: dict, query: str, scope: str, limit: int = 30,
                   exact: bool = False, documents=None) -> list[Candidate]:
    literals = [query.strip().strip('"')] if exact else literal_terms(query)
    if not literals:
        return []
    if exact and documents is not None:
        # Exact strings may cross indexing boundaries. Locate them in the
        # versioned document and create a literal evidence window, rather than
        # requiring a phrase to fit an embedding chunk.
        needle = literals[0]
        if not needle:
            return []
        found = []
        for document in documents.values():
            if scope != "all" and document.layer != scope:
                continue
            position = 0
            for _ in range(2):
                match = document.text.find(needle, position)
                if match < 0:
                    break
                start, end = max(0, match - 100), min(len(document.text), match + len(needle) + 200)
                text = document.text[start:end]
                section = next((p.section for p in document.passages if p.start_offset <= match < p.end_offset), "")
                passage = Passage(digest(f"literal\0{document.path}\0{start}\0{end}"), document.path, section,
                    document.text.count("\n", 0, start) + 1,
                    document.text.count("\n", 0, max(start, end - 1)) + 1,
                    text, digest(text), start, end)
                found.append(Candidate(passage, 1.0, {"literal"}))
                position = match + len(needle)
        return sorted(found, key=lambda c: (len(c.passage.text), c.passage.path, c.passage.start_offset))[:limit]
    found = []
    for passage in passages.values():
        if scope != "all" and not passage.path.startswith(scope + "/"):
            continue
        text = passage.text if exact else passage.text.casefold()
        count = sum((value if exact else value.casefold()) in text for value in literals)
        if count:
            found.append(Candidate(passage, float(count), {"literal"}))
    return sorted(found, key=lambda c: (-c.score, len(c.passage.text), c.passage.id))[:limit]
