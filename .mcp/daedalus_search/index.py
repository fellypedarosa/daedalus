"""Immutable SQLite generations, incremental embeddings and atomic publication."""
from __future__ import annotations

import fcntl
import json
import os
import sqlite3
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from .documents import (Resolver, add_catalog_aliases, parse_document, scan_paths,
                        stable_read, text_tokens)
from .models import (PARSER_VERSION, SCHEMA_VERSION, Document, Passage, Relation,
                     SearchUnavailable, digest)

DDL = """
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE documents(path TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE passages(id TEXT UNIQUE NOT NULL, path TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX passages_path ON passages(path);
CREATE VIRTUAL TABLE passages_fts USING fts5(title, aliases, section, body, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE relations(source TEXT NOT NULL, target TEXT, kind TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX relations_target ON relations(target);
CREATE TABLE embeddings(passage_id TEXT PRIMARY KEY, model TEXT NOT NULL,
                        input_hash TEXT NOT NULL, dimension INTEGER NOT NULL, vector BLOB NOT NULL);
"""


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def load_documents(connection) -> dict[str, Document]:
    result = {}
    for row in connection.execute("SELECT path, payload FROM documents ORDER BY path"):
        value = json.loads(row["payload"])
        value["passages"] = [Passage(**v) for v in value["passages"]]
        value["relations"] = [Relation(**v) for v in value["relations"]]
        result[row["path"]] = Document(**value)
    return result


class IndexStore:
    def __init__(self, root: Path, directory: Path):
        self.root = root.resolve()
        self.directory = directory.resolve()
        if self.directory == self.root or any(self.directory.is_relative_to(self.root / p) for p in ("wiki", "raw")):
            raise ValueError("Index directory must be outside knowledge layers")
        self.directory.mkdir(parents=True, exist_ok=True)

    def current(self) -> Path:
        try:
            generation = json.loads((self.directory / "current.json").read_text())["file"]
            if Path(generation).name != generation or not generation.startswith("generation-"):
                raise ValueError("Invalid generation filename")
            path = self.directory / generation
            if not path.is_file():
                raise FileNotFoundError(path)
            return path
        except (OSError, ValueError, KeyError) as exc:
            raise SearchUnavailable("Search index unavailable; run .mcp/scripts/reindex_search.py from the repository root") from exc

    def build(self, encoder=None, max_tokens: int = 256) -> dict:
        from daedalus_ingest.storage import IngestError, vault_lock
        try:
            with vault_lock(self.root, nonblocking=True, indexing=True):
                with (self.directory / "writer.lock").open("a") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    return self._build(encoder, max_tokens)
        except IngestError as exc:
            raise SearchUnavailable(str(exc)) from exc

    def _build(self, encoder, max_tokens) -> dict:
        started = time.perf_counter()
        previous = None
        try:
            previous = connect(self.current())
        except (SearchUnavailable, sqlite3.DatabaseError):
            pass
        try:
            return self._prepare(previous, encoder, max_tokens, started)
        finally:
            if previous:
                previous.close()

    def _prepare(self, previous, encoder, max_tokens, started):
        old_meta, old_docs = {}, {}
        if previous:
            old_meta = {r["key"]: json.loads(r["value"]) for r in previous.execute("SELECT * FROM metadata")}
            if old_meta.get("vault") != str(self.root):
                raise SearchUnavailable("Index belongs to another vault; choose a separate index directory")
            if old_meta.get("schema") == SCHEMA_VERSION:
                old_docs = load_documents(previous)
        cache = previous if old_meta.get("schema") == SCHEMA_VERSION else None
        if encoder:
            max_tokens = min(max_tokens, encoder.max_length - 48)
        config = {"parser": PARSER_VERSION, "max_tokens": max_tokens,
                  "tokenizer": encoder.identity if encoder else "utf8-conservative-v1"}
        catalog = self.root / "wiki/index.md"
        if catalog.exists():
            config["catalog_hash"] = digest(stable_read(self.root, "wiki/index.md")[0])
        documents, changed = {}, 0
        for path in scan_paths(self.root):
            data, _ = stable_read(self.root, path)
            old = old_docs.get(path)
            if old and old.hash == digest(data) and config == old_meta.get("parser_config"):
                # Drop previous catalog-derived aliases when the catalog changes
                # by reparsing (its hash is part of parser_config).
                documents[path] = old
            else:
                documents[path] = parse_document(self.root, path, max_tokens=max_tokens,
                    count_tokens=encoder.count_tokens if encoder else text_tokens)
                changed += 1
        add_catalog_aliases(self.root, documents)
        Resolver(self.root, documents).resolve_relations()
        manifest = {path: doc.hash for path, doc in documents.items()}
        manifest_hash = digest(json.dumps(manifest, sort_keys=True))
        model = encoder.identity if encoder else None
        if previous and old_meta.get("manifest_hash") == manifest_hash and old_meta.get("parser_config") == config and old_meta.get("model") == model:
            return {"generation": old_meta["generation"], "documents": len(documents),
                    "changed": 0, "embedded": 0, "reused_embeddings": old_meta.get("embedding_count", 0),
                    "seconds": time.perf_counter() - started, "unchanged": True}

        generation = uuid.uuid4().hex
        temporary = self.directory / f"building-{generation}.sqlite"
        published = self.directory / f"generation-{generation}.sqlite"
        connection = sqlite3.connect(temporary)
        embedded, reused = 0, 0
        vector_cache = None
        try:
            connection.executescript(DDL)
            if encoder:
                vector_cache = sqlite3.connect(self.directory / "embedding-cache.sqlite")
                vector_cache.execute("CREATE TABLE IF NOT EXISTS vectors (model TEXT, input_hash TEXT, dimension INTEGER, vector BLOB, PRIMARY KEY(model,input_hash))")
                vector_cache.commit()
            pending = []
            for doc in documents.values():
                connection.execute("INSERT INTO documents VALUES (?,?)", (doc.path, json.dumps(asdict(doc), ensure_ascii=False, default=str)))
                for relation in doc.relations:
                    connection.execute("INSERT INTO relations VALUES (?,?,?,?)", (relation.source, relation.target,
                        relation.kind, json.dumps(asdict(relation), ensure_ascii=False)))
                for passage in doc.passages:
                    rowid = connection.execute("INSERT INTO passages VALUES (?,?,?)", (passage.id, doc.path,
                        json.dumps(asdict(passage), ensure_ascii=False))).lastrowid
                    connection.execute("INSERT INTO passages_fts(rowid,title,aliases,section,body) VALUES (?,?,?,?,?)",
                        (rowid, doc.title.replace("_", " "), " ".join(doc.aliases), passage.section, passage.text))
                    if encoder:
                        text = encoder.passage_input(doc, passage)
                        input_hash = digest(text)
                        cached = cache.execute("SELECT * FROM embeddings WHERE passage_id=? AND model=? AND input_hash=?",
                            (passage.id, model, input_hash)).fetchone() if cache else None
                        if cached:
                            connection.execute("INSERT INTO embeddings VALUES (?,?,?,?,?)", tuple(cached))
                            reused += 1
                        else:
                            cached_vector = vector_cache.execute("SELECT dimension, vector FROM vectors WHERE model=? AND input_hash=?",
                                                                 (model, input_hash)).fetchone()
                            if cached_vector:
                                connection.execute("INSERT INTO embeddings VALUES (?,?,?,?,?)", (passage.id, model, input_hash, *cached_vector))
                                reused += 1
                            else:
                                pending.append((passage.id, input_hash, text))
            if encoder:
                for offset in range(0, len(pending), 8):
                    batch = pending[offset:offset + 8]
                    vectors = encoder.encode([item[2] for item in batch])
                    if len(vectors) != len(batch):
                        raise ValueError("Encoder returned an incomplete batch")
                    for item, vector in zip(batch, vectors):
                        raw_vector = vector.astype("<f4").tobytes()
                        connection.execute("INSERT INTO embeddings VALUES (?,?,?,?,?)", (item[0], model, item[1],
                            len(vector), raw_vector))
                        vector_cache.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?,?)",
                                             (model, item[1], len(vector), raw_vector))
                        embedded += 1
                    # Persist resumable computation without publishing a partial
                    # document/graph generation. A killed build can reuse it.
                    vector_cache.commit()
            metadata = {"schema": SCHEMA_VERSION, "parser_config": config, "generation": generation,
                "manifest_hash": manifest_hash, "manifest": manifest, "model": model,
                "model_spec": encoder.spec if encoder else None, "embedding_count": embedded + reused,
                "created_at": time.time(), "vault": str(self.root)}
            for key, value in metadata.items():
                connection.execute("INSERT INTO metadata VALUES (?,?)", (key, json.dumps(value)))
            connection.commit()
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise SearchUnavailable("Index integrity verification failed")
            connection.execute("INSERT INTO passages_fts(passages_fts) VALUES ('integrity-check')")
            connection.commit()
            # Do not publish a generation built from files that changed midway.
            for path, expected in manifest.items():
                if digest(stable_read(self.root, path)[0]) != expected:
                    raise OSError(f"Knowledge changed during index build: {path}")
            if scan_paths(self.root) != list(manifest):
                raise OSError("Knowledge file list changed during index build")
            connection.close()
            with temporary.open("rb") as file:
                os.fsync(file.fileno())
            temporary.rename(published)
            pointer = self.directory / f"current-{generation}.tmp"
            with pointer.open("w") as file:
                json.dump({"file": published.name}, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(pointer, self.directory / "current.json")
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return {"generation": generation, "documents": len(documents), "passages": sum(len(d.passages) for d in documents.values()),
                "changed": changed, "removed": len(set(old_docs) - set(documents)), "embedded": embedded,
                "reused_embeddings": reused, "seconds": time.perf_counter() - started, "unchanged": False}
        finally:
            connection.close()
            if vector_cache:
                vector_cache.close()
            temporary.unlink(missing_ok=True)

    def snapshot(self):
        path = self.current()
        connection = connect(path)
        try:
            metadata = {r["key"]: json.loads(r["value"]) for r in connection.execute("SELECT * FROM metadata")}
            if metadata.get("schema") != SCHEMA_VERSION or metadata.get("vault") != str(self.root):
                raise SearchUnavailable("Index belongs to another vault or schema; rebuild it")
            return connection, metadata, load_documents(connection)
        except Exception:
            connection.close()
            raise
