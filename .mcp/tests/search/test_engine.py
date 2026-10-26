from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from daedalus_search.documents import Resolver, parse_document, scan_paths
from daedalus_search.engine import SearchEngine, render_text
from daedalus_search.index import IndexStore
from daedalus_search.lexical import query_terms
from daedalus_search.models import AmbiguousReference, Candidate, SearchUnavailable, digest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/search"


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.vault = self.base / "vault"
        shutil.copytree(FIXTURE, self.vault)
        (self.vault / "AGENTS.md").write_text("operational-only-marker")
        self.engine = SearchEngine(self.vault, self.base / "index", interval=0)
        self.engine.prepare()

    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()

    def test_literal_provenance_and_read_only_sources(self):
        before = {str(p): digest(p.read_bytes()) for p in self.vault.rglob("*.md")}
        result = self.engine.search("D3cold", mode="exact")
        self.assertEqual(result["results"][0]["path"], "wiki/Other/Drivers.md")
        self.assertFalse(result["score_is_probability"])
        for entry in result["results"]:
            text = (self.vault / entry["path"]).read_text()
            self.assertEqual(digest(text), entry["document_hash"])
            for snippet in entry["passages"]:
                self.assertEqual(text[snippet["start_offset"]:snippet["end_offset"]], snippet["text"])
                self.assertEqual(text.count("\n", 0, snippet["start_offset"]) + 1, snippet["start_line"])
        self.engine.reindex(semantic=False)
        self.assertEqual(before, {str(p): digest(p.read_bytes()) for p in self.vault.rglob("*.md")})

    def test_scope_raw_only_disconnected_and_admin_exclusion(self):
        self.assertEqual(self.engine.search("orphan-raw-782", mode="exact")["results"][0]["layer"], "raw")
        self.assertEqual(self.engine.search("azimuth-raw-731", scope="wiki", mode="exact")["results"], [])
        self.assertEqual(self.engine.search("mustnotbesearchable", mode="exact")["results"], [])
        self.assertEqual(self.engine.search("operational-only-marker", mode="exact")["results"], [])

    def test_paths_aliases_ambiguities_and_source_links(self):
        resolver = self.engine.resolver()
        self.assertEqual(resolver.resolve("Access through NAT"), "wiki/Networking/Tunnels.md")
        self.assertEqual(resolver.resolve("Túneis SSH"), "wiki/Networking/Tunnels.md")
        self.assertEqual(resolver.resolve("wiki/Other/Duplicate.md"), "wiki/Other/Duplicate.md")
        with self.assertRaises(AmbiguousReference) as context:
            resolver.resolve("Duplicate")
        self.assertEqual(len(context.exception.candidates), 2)
        doc = self.engine.catalog()["wiki/Networking/Tunnels.md"]
        self.assertTrue(any(r.target == "raw/ai/Tunnel_Source.md" and r.kind == "source" for r in doc.relations))
        self.assertTrue(any(r.status == "ambiguous" for r in doc.relations))

    def test_file_uri_relative_markdown_and_moved_vault(self):
        resolver = self.engine.resolver()
        path = self.vault / "raw/ai/Tunnel_Source.md"
        self.assertEqual(resolver.resolve(path.as_uri() + "#Reconnection"), "raw/ai/Tunnel_Source.md")
        self.assertEqual(resolver.resolve("../../raw/ai/Tunnel_Source.md", "wiki/Networking/Tunnels.md"), "raw/ai/Tunnel_Source.md")
        self.assertEqual(resolver.resolve("file:///old/location/raw/ai/Tunnel_Source.md"), "raw/ai/Tunnel_Source.md")
        self.assertEqual(resolver.candidates("file:///etc/passwd"), [])

    def test_cataloged_source_reference_survives_archival(self):
        directory = self.vault / "raw/ai/cataloged"
        directory.mkdir()
        (directory / "Archived.md").write_text("# Archived\nA source moved by ingestion.\n")
        self.engine.reindex(semantic=False)
        resolver = self.engine.resolver()
        self.assertEqual(resolver.resolve("raw/ai/Archived.md"), "raw/ai/cataloged/Archived.md")
        self.assertEqual(resolver.resolve("file:///old/vault/raw/ai/Archived.md"), "raw/ai/cataloged/Archived.md")

    def test_boundaries_no_symlink_escape(self):
        outside = self.base / "Outside.md"
        outside.write_text("outside-marker")
        (self.vault / "wiki/escape.md").symlink_to(outside)
        self.assertNotIn("wiki/escape.md", scan_paths(self.vault))
        self.assertEqual(self.engine.resolver().candidates("../AGENTS.md"), [])
        with self.assertRaises(ValueError):
            IndexStore(self.vault, self.vault / "raw/index")

    def test_external_links_attachments_and_local_anchors_are_not_ghosts(self):
        (self.vault / "wiki/Other/Links.md").write_text(
            "# Links\n[External](https://example.org/reference)\n"
            "[[image.png]]\n[[#Links]]\n")
        self.engine.reindex(semantic=False)
        relations = self.engine.catalog()["wiki/Other/Links.md"].relations
        self.assertEqual([r.status for r in relations], ["external", "attachment", "resolved"])
        self.assertEqual(relations[-1].target, "wiki/Other/Links.md")

    def test_query_normalization_and_technical_literals(self):
        self.assertNotIn("a", query_terms("Qual é a diferença entre backup e RAID?"))
        self.assertIn("raid", query_terms("Qual é a diferença entre backup e RAID?"))
        for term in ("C++", ".env", "--force", "1.2.3", "D3cold"):
            with self.subTest(term=term):
                result = self.engine.search(term, mode="exact")
                self.assertEqual(result["results"][0]["path"], "wiki/Other/Drivers.md")
        self.assertEqual(self.engine.search('" OR * NEAR(()') ["results"], [])
        self.assertFalse(self.engine.search("d3COLD", mode="exact")["results"])

    def test_exact_phrase_crosses_embedding_boundaries(self):
        path = self.vault / "raw/ai/Boundary.md"
        path.write_text("# Boundary\n\n" + " ".join(f"word{i:05d}" for i in range(500)))
        self.engine.max_tokens = 64
        self.engine.reindex(semantic=False)
        doc = self.engine.catalog()["raw/ai/Boundary.md"]
        boundary = doc.passages[0].end_offset
        needle = doc.text[boundary - 12:boundary + 12].strip()
        self.assertFalse(any(needle in p.text for p in doc.passages))
        result = self.engine.search(needle, mode="exact")
        self.assertTrue(any(needle in p["text"] for r in result["results"] for p in r["passages"]))

    def test_invalid_inputs(self):
        for kwargs in ({"query": " "}, {"query": "x", "limit": 0}, {"query": "x", "limit": True},
                       {"query": "x", "scope": "../"}, {"query": "x", "mode": "unknown"},
                       {"query": "x" * 2001}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.engine.search(**kwargs)

    def test_incremental_rename_remove_and_noop(self):
        first = self.engine.store.current()
        report = self.engine.reindex(semantic=False)
        self.assertTrue(report["unchanged"])
        self.assertEqual(self.engine.store.current(), first)
        old = self.vault / "raw/ai/Isolated.md"
        new = old.with_name("Renamed.md")
        old.rename(new)
        report = self.engine.reindex(semantic=False)
        self.assertEqual(report["removed"], 1)
        self.assertEqual(report["changed"], 1)
        new.unlink()
        self.engine.reindex(semantic=False)
        self.assertEqual(self.engine.search("orphan-raw-782", mode="exact")["results"], [])

    def test_stale_citations_omitted_until_reindex(self):
        path = self.vault / "wiki/Other/Drivers.md"
        path.write_text("# Replaced\nA new generation.\n")
        result = self.engine.search("D3cold", mode="exact")
        self.assertEqual(result["results"], [])
        self.assertTrue(any("index_update_pending" in w for w in result["warnings"]))
        self.engine.reindex(semantic=False)
        self.assertFalse(self.engine.status()["pending_update"])

    def test_restart_restore_generation_and_other_vault_rejected(self):
        pointer = self.base / "index/current.json"
        original = pointer.read_text()
        (self.vault / "raw/ai/Added.md").write_text("# Added\nversion-two-only-marker\n")
        self.engine.reindex(semantic=False)
        self.assertTrue(self.engine.search("version-two-only-marker", mode="exact")["results"])
        self.engine.close()
        pointer.write_text(original)
        restored = SearchEngine(self.vault, self.base / "index", interval=0)
        self.assertTrue(restored.search("D3cold", mode="exact")["results"])
        self.assertFalse(restored.search("version-two-only-marker", mode="exact")["results"])
        restored.close()
        another = self.base / "another"
        shutil.copytree(FIXTURE, another)
        with self.assertRaises(SearchUnavailable):
            IndexStore(another, self.base / "index").build()

    def test_failed_update_retains_usable_previous_generation(self):
        generation = self.engine.store.current()
        (self.vault / "raw/ai/new.md").write_text("# New\nA new source.\n")
        with patch("daedalus_search.index.parse_document", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.engine.reindex(semantic=False)
        self.assertEqual(self.engine.store.current(), generation)
        self.assertEqual(self.engine.search("D3cold", mode="exact")["results"][0]["layer"], "wiki")

    def test_queries_continue_during_unpublished_update(self):
        entered, release = threading.Event(), threading.Event()
        original = parse_document
        errors = []
        def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise TimeoutError("test synchronization")
            return original(*args, **kwargs)
        def build():
            try:
                self.engine.reindex(semantic=False)
            except Exception as exc:
                errors.append(exc)
        (self.vault / "raw/ai/new.md").write_text("# New\nAdded evidence.\n")
        old_generation = self.engine.search("D3cold", mode="exact")["generation"]
        with patch("daedalus_search.index.parse_document", side_effect=delayed):
            worker = threading.Thread(target=build)
            worker.start()
            try:
                self.assertTrue(entered.wait(3))
                self.assertEqual(self.engine.search("D3cold", mode="exact")["generation"], old_generation)
            finally:
                release.set()
                worker.join(5)
        self.assertFalse(errors)
        self.assertNotEqual(self.engine.search("D3cold", mode="exact")["generation"], old_generation)

    def test_parser_long_lines_blocks_and_offsets(self):
        path = self.vault / "raw/ai/Long.md"
        path.write_text("---\ntags: [long]\n---\n# Long\n\n" + "comprehensible text " * 600 +
                        "\n\n```python\nprint('hello')\n```\n\n| A | B |\n|---|---|\n|1|2|\n")
        doc = parse_document(self.vault, "raw/ai/Long.md", max_tokens=64)
        self.assertGreater(len(doc.passages), 10)
        for p in doc.passages:
            self.assertEqual(doc.text[p.start_offset:p.end_offset], p.text)
        self.assertTrue(any("```python\nprint('hello')\n```" in p.text for p in doc.passages))
        self.assertTrue(any("| A | B |" in p.text and "|1|2|" in p.text for p in doc.passages))
        self.assertFalse(any(p.text.strip() == "# Long" for p in doc.passages))
        self.assertNotIn("Not_A_Real_Link", [r.reference for r in self.engine.catalog()["wiki/Other/Drivers.md"].relations])

    def test_graph_bounded_with_provenance_not_authorship(self):
        result = self.engine.search("NAT connection firewall", scope="wiki")
        for entry in result["results"]:
            for p in entry["passages"]:
                self.assertTrue(all(v["relation"] != "authorship" for v in p["via"]))
                for relation in p["via"]:
                    self.assertEqual(relation["reference_document_hash"], digest((self.vault / relation["reference_document"]).read_bytes()))
        self.assertLessEqual(len(result["results"]), 5)
        self.assertIn("wiki/Networking/Tunnels.md", [r["path"] for r in result["results"]])

    def test_missing_model_fallback_and_themes(self):
        self.engine.model_dir = self.base / "missing-model"
        self.engine.reindex()
        result = self.engine.search("network storage", mode="themes")
        self.assertEqual(result["retrieval"], "lexical")
        self.assertTrue(any("lexical_only" in w for w in result["warnings"]))
        self.assertTrue(self.engine.status()["ready"])
        self.assertIn("generation=", render_text(result))

    def test_graph_discovery_does_not_double_vote_for_existing_candidates(self):
        self.engine.enable_graph = False
        query = "RAID backup tunnel connection"
        expected = [r["path"] for r in self.engine.search(query)["results"]]
        def rediscover(candidates, *args, **kwargs):
            item = candidates[-1]
            return [Candidate(item.passage, 1000, {"graph"}, [{"reference_document": item.passage.path,
                "from": item.passage.path, "to": item.passage.path, "relation": "topic", "line": 1}])]
        self.engine.enable_graph = True
        with patch("daedalus_search.engine.expand", side_effect=rediscover):
            actual = [r["path"] for r in self.engine.search(query)["results"]]
        self.assertEqual(expected, actual)

    def test_context_budget_and_corrupt_index_are_explicit(self):
        self.engine.max_characters = 1024
        result = self.engine.search("RAID backup", limit=5)
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False)), 1024)
        self.engine.close()
        self.engine.store.current().write_bytes(b"corrupt index")
        self.assertFalse(self.engine.status()["ready"])
        with self.assertRaises(sqlite3.DatabaseError):
            self.engine.search("backup")


if __name__ == "__main__":
    unittest.main()
