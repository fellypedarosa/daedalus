"""Knowledge search orchestration, live citation verification and text/JSON views."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

from .documents import Resolver, safe_path, stable_read
from .graph import expand
from .index import IndexStore
from .lexical import lexical_search, literal_search, query_terms
from .models import Candidate, SearchUnavailable, digest
from .ranking import fuse, select
from .semantic import LocalEncoder, LocalReranker, SemanticSearch

LOGGER = logging.getLogger(__name__)


class SearchEngine:
    def __init__(self, root: Path, index_dir: Path | None = None, *, model_dir: Path | None = None,
                 reranker_dir: Path | None = None, max_tokens=256, interval=60,
                 enable_graph=True, max_characters=18000):
        self.root = Path(root).resolve()
        default_key = json.dumps({"vault": str(self.root), "tokens": max_tokens,
                                  "model": str(Path(model_dir).resolve()) if model_dir else None}, sort_keys=True)
        default_dir = Path(tempfile.gettempdir()) / "daedalus-search" / digest(default_key)[:16]
        self.store = IndexStore(self.root, Path(index_dir) if index_dir else default_dir)
        self.model_dir = Path(model_dir) if model_dir else None
        self.reranker_dir = Path(reranker_dir) if reranker_dir else None
        self.max_tokens = max_tokens
        self.interval = interval
        self.enable_graph = enable_graph
        self.max_characters = max_characters
        if max_characters < 1024:
            raise ValueError("Search context budget must be at least 1024 characters")
        self.encoder = None
        self.reranker = None
        self._snapshot = None
        self._semantic = None
        self._generation = None
        self._lock = threading.RLock()
        self._update_lock = threading.Lock()
        self._models_lock = threading.Lock()
        self._models_attempted = False
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._worker = None
        self.last_update = None
        self.last_error = None
        self.semantic_error = None
        self.pending_update = False

    @classmethod
    def from_environment(cls, root):
        return cls(root, os.environ.get("DAEDALUS_INDEX_DIR"),
                   model_dir=os.environ.get("DAEDALUS_MODEL_DIR"),
                   reranker_dir=os.environ.get("DAEDALUS_RERANKER_DIR"),
                   max_tokens=int(os.environ.get("DAEDALUS_PASSAGE_TOKENS", "256")),
                   interval=float(os.environ.get("DAEDALUS_INDEX_INTERVAL", "60")),
                   enable_graph=os.environ.get("DAEDALUS_GRAPH", "0") == "1",
                   max_characters=int(os.environ.get("DAEDALUS_CONTEXT_CHARS", "18000")))

    def prepare(self):
        try:
            self.store.current()
        except SearchUnavailable:
            self.store.build(max_tokens=self.max_tokens)
        if not self._models_attempted and (self.model_dir or self.reranker_dir):
            self.load_models()
        # Validate existing generations, too: a corrupt/wrong-vault cache is not
        # a healthy search service and must not become an empty result.
        with self._lock:
            self._load()

    def _load(self):
        filename = self.store.current().name
        if filename == self._generation:
            if self.encoder and self._snapshot[1].get("model") == self.encoder.identity and self._semantic is None:
                self._semantic = SemanticSearch(self.encoder, self._snapshot[0])
            return
        snapshot = self.store.snapshot()
        connection, metadata, documents = snapshot
        passages = {p.id: p for d in documents.values() for p in d.passages}
        semantic = None
        if self.encoder and metadata.get("model") == self.encoder.identity:
            semantic = SemanticSearch(self.encoder, connection)
        old = self._snapshot
        self._snapshot = (connection, metadata, documents, passages)
        self._generation, self._semantic = filename, semantic
        if old:
            old[0].close()

    def load_models(self):
        with self._models_lock:
            self._load_models()

    def _load_models(self):
        self._models_attempted = True
        # Loading artifacts is local-only, verifies checksums, and never downloads.
        if self.model_dir and not self.encoder:
            try:
                self.encoder = LocalEncoder(self.model_dir)
                self.semantic_error = None
            except Exception as exc:
                self.semantic_error = type(exc).__name__
                LOGGER.warning("Semantic model unavailable (%s); retaining lexical retrieval", type(exc).__name__)
        if self.reranker_dir and not self.reranker:
            try:
                self.reranker = LocalReranker(self.reranker_dir)
            except Exception as exc:
                LOGGER.warning("Reranker unavailable (%s)", type(exc).__name__)

    def reindex(self, semantic=True):
        with self._update_lock:
            if semantic:
                self.load_models()
            report = self.store.build(self.encoder if semantic else None, self.max_tokens)
            with self._lock:
                self._load()
                self.last_update = time.time()
                self.last_error = None
                self.pending_update = False
            return report

    def start(self):
        self.prepare()
        if self._worker or self.interval <= 0:
            return
        def update():
            while not self._stop.is_set():
                try:
                    self.reindex()
                except Exception as exc:
                    self.last_error = type(exc).__name__
                    LOGGER.warning("Index update failed (%s); retaining previous generation", type(exc).__name__)
                self._wake.wait(self.interval)
                self._wake.clear()
        self._worker = threading.Thread(target=update, name="daedalus-index", daemon=True)
        self._worker.start()

    def request_update(self):
        """Wake indexing after ingestion; notes are never reapplied on failure."""
        self.pending_update = True
        if self._worker and self._worker.is_alive():
            self._wake.set()
        else:
            def once():
                try:
                    self.reindex()
                except Exception as exc:
                    self.last_error = type(exc).__name__
            self._worker = threading.Thread(target=once, name="daedalus-ingest-index", daemon=True)
            self._worker.start()

    def close(self):
        self._stop.set()
        self._wake.set()
        if self._worker:
            self._worker.join(timeout=5)
        with self._lock:
            if self._snapshot:
                self._snapshot[0].close()
                self._snapshot = None
                self._generation = None

    def status(self):
        with self._lock:
            try:
                self._load()
                metadata = self._snapshot[1]
                return {"ready": True, "generation": metadata["generation"],
                        "indexed_at": metadata["created_at"], "last_update": self.last_update,
                        "retrieval": "hybrid" if self._semantic else "lexical",
                        "documents": len(self._snapshot[2]), "passages": len(self._snapshot[3]),
                        "pending_update": self.pending_update, "last_error": self.last_error,
                        "semantic_error": self.semantic_error}
            except (SearchUnavailable, sqlite3.DatabaseError, ValueError, KeyError):
                return {"ready": False, "last_error": self.last_error or "index_unavailable"}

    def catalog(self):
        self.prepare()
        with self._lock:
            self._load()
            return self._snapshot[2]

    def resolver(self):
        return Resolver(self.root, self.catalog())

    def search(self, query: str, limit: int = 5, scope: str = "all", mode: str = "auto") -> dict:
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError("query must contain 1–2000 characters")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError("limit must be an integer between 1 and 20")
        if scope not in {"all", "wiki", "raw"} or mode not in {"auto", "exact", "themes"}:
            raise ValueError("Invalid scope or mode")
        self.prepare()
        started = time.perf_counter()
        with self._lock:
            self._load()
            connection, metadata, documents, passages = self._snapshot
            warnings = []
            verified, texts = {}, {}
            def current(path):
                if path not in verified:
                    try:
                        data, text = stable_read(self.root, path)
                        verified[path] = digest(data) == documents[path].hash
                        texts[path] = text
                    except (OSError, ValueError):
                        verified[path] = False
                return verified[path]
            semantic = self._semantic
            if mode == "exact":
                candidates = literal_search(passages, query, scope, 200, exact=True, documents=documents)
                retrieval = "literal"
            else:
                lexical = lexical_search(connection, query, passages, scope, 30)
                literal = literal_search(passages, query, scope, 30)
                dense = []
                if semantic:
                    try:
                        dense = semantic.search(query, passages, scope, 30)
                    except Exception as exc:
                        warnings.append("semantic_unavailable:" + type(exc).__name__)
                        semantic = None
                retrieval = "hybrid" if semantic else "lexical"
                candidates = fuse(lexical, dense, literal)
                if not semantic:
                    warnings.append("lexical_only: multilingual paraphrase recall may be limited")
                elif not lexical and not literal:
                    warnings.append("semantic_matches_only: verify whether passages support the requested fact")
                if self.enable_graph and candidates:
                    extra = expand(candidates, documents, connection, passages, query, scope, semantic)
                    valid = []
                    for item in extra:
                        item.via = [{**relation, "reference_document_hash": documents[relation["reference_document"]].hash}
                                    for relation in item.via if current(relation["reference_document"])]
                        if item.via:
                            valid.append(item)
                    if valid:
                        # Links discover candidates; they do not cast another
                        # relevance vote. Re-score the union with the same
                        # query-based channels before adding provenance.
                        pool = {c.passage.id for c in candidates + valid}
                        lexical_pool = [c for c in lexical_search(connection, query, passages, scope, len(passages))
                                        if c.passage.id in pool]
                        semantic_pool = [c for c in semantic.search(query, passages, scope, len(passages))
                                         if c.passage.id in pool] if semantic else []
                        literal_pool = [c for c in literal_search(passages, query, scope, len(passages))
                                        if c.passage.id in pool]
                        candidates = fuse(lexical_pool, semantic_pool, literal_pool)
                        relations = {c.passage.id: c.via for c in valid}
                        for item in candidates:
                            if item.passage.id in relations:
                                item.channels.add("graph")
                                item.via = relations[item.passage.id]
                if mode == "themes":
                    # Include relevant representatives beyond a global top-30,
                    # including disconnected/raw-only documents.
                    def representatives(items):
                        unique = {}
                        for item in items:
                            unique.setdefault(item.passage.path, item)
                        return list(unique.values())
                    thematic = representatives(lexical_search(connection, query, passages, scope, max(100, len(passages))))
                    if semantic:
                        thematic = fuse(thematic, representatives(semantic.search(query, passages, scope, max(100, len(passages)))))
                    candidates = fuse(candidates, thematic)
                    warnings.append("theme_coverage_is_limited_to_selected_evidence")
                if self.reranker and candidates:
                    try:
                        candidates = self.reranker.rank(query, candidates[:60])
                    except Exception as exc:
                        warnings.append("reranker_unavailable:" + type(exc).__name__)
            # Verify each selected candidate against current source bytes before
            # applying limit, so stale results cannot crowd out current ones.
            checked = []
            for candidate in candidates:
                path = candidate.passage.path
                current(path)
                passage = candidate.passage
                if verified[path] and texts[path][passage.start_offset:passage.end_offset] == passage.text:
                    checked.append(candidate)
                else:
                    self.pending_update = True
            if self.pending_update or any(not v for v in verified.values()):
                warnings.append("index_update_pending: changed or missing documents omitted")
            selected = select(checked, documents, limit, themes=mode == "themes")
            results, used, truncated = [], 0, False
            for document, items in selected:
                snippets = []
                for item in items:
                    p = item.passage
                    available = self.max_characters - used
                    if available <= 0:
                        truncated = True
                        break
                    value = p.text[:min(2400, available)]
                    excerpt = len(value) != len(p.text)
                    truncated |= excerpt
                    used += len(value)
                    snippets.append({"section": p.section, "text": value,
                        "start_line": p.start_line, "end_line": p.start_line + value.count("\n") - int(value.endswith("\n")),
                        "start_offset": p.start_offset, "end_offset": p.start_offset + len(value),
                        "passage_hash": p.hash, "excerpt": excerpt,
                        "channels": sorted(item.channels), "via": item.via})
                if snippets:
                    results.append({"path": document.path, "layer": document.layer, "title": document.title,
                        "domain": document.domain, "tags": document.tags, "document_hash": document.hash,
                        "score": items[0].score, "sources": sorted({r.target for r in document.relations if r.kind == "source" and r.target}),
                        "passages": snippets})
                else:
                    truncated = True
                    break
            if not results:
                warnings.append("no_verified_evidence_found: this does not prove absence from the corpus")
            response = {"schema_version": 1, "query": query, "scope": scope, "mode": mode,
                "generation": metadata["generation"], "retrieval": retrieval,
                "score_is_probability": False, "truncated": truncated, "warnings": warnings,
                "results": results, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)}
            while len(json.dumps(response, ensure_ascii=False)) > self.max_characters and response["results"]:
                response["truncated"] = True
                entry = response["results"][-1]
                passage = entry["passages"][-1]
                excess = len(json.dumps(response, ensure_ascii=False)) - self.max_characters
                if len(passage["text"]) - excess > 100:
                    passage["text"] = passage["text"][:len(passage["text"]) - excess - 16]
                    passage["end_offset"] = passage["start_offset"] + len(passage["text"])
                    passage["end_line"] = passage["start_line"] + passage["text"].count("\n") - int(passage["text"].endswith("\n"))
                    passage["excerpt"] = True
                else:
                    entry["passages"].pop()
                    if not entry["passages"]:
                        response["results"].pop()
            if len(json.dumps(response, ensure_ascii=False)) > self.max_characters:
                raise ValueError("Context budget is too small for query and response metadata")
            return response


def render_text(result: dict) -> str:
    lines = [f"Found {len(result['results'])} result(s) for {result['query']!r} "
             f"(scope={result['scope']}, retrieval={result['retrieval']}, generation={result['generation']}):"]
    for entry in result["results"]:
        lines.append(f"\n{entry['path']} [{entry['layer']}] — {entry['title']}")
        lines.append(f"Document SHA-256: {entry['document_hash']}")
        for passage in entry["passages"]:
            lines.append(f"L{passage['start_line']}–L{passage['end_line']} | {passage['section']} "
                         f"| {', '.join(passage['channels'])}")
            lines.append(passage["text"])
            if passage["via"]:
                lines.append("Relations: " + json.dumps(passage["via"], ensure_ascii=False))
        if entry["sources"]:
            lines.append("Sources: " + ", ".join(entry["sources"]))
    if result["warnings"]:
        lines.append("\nWarnings: " + "; ".join(result["warnings"]))
    if result["truncated"]:
        lines.append("Context shortened; use read(path) for complete documents.")
    return "\n".join(lines)
