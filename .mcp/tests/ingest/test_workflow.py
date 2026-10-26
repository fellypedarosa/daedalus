from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from daedalus_ingest import apply as application
from daedalus_ingest.service import IngestService
from daedalus_ingest.sources import archive_path, path_for, read_bytes
from daedalus_ingest.storage import IngestError, load_operation, sha, state_dir
from daedalus_search.engine import SearchEngine
from daedalus_search.models import SearchUnavailable

SOURCE = ("# Synthetic source\n\n"
          "A tunnel forwards a local service through an outbound connection.\n"
          "The procedure is specific to the lab environment.\n\n"
          "The historical host used a RAID array.\n"
          "That does not define the current server architecture.\n"
          "End of synthetic source.\n")
SOURCE_PATH = "raw/local/Source.md"
NEW_NODE = "wiki/Concepts/Tunnels.md"


def node(source=SOURCE_PATH, title="Tunnels"):
    return (f"---\ntags: [networking, synthetic]\ndate_created: 2026-10-25\n"
            f"sources:\n  - '[[{source}]]'\n---\n# {title}\n\nAutor: [[LLM]]\n\n"
            "A lab tunnel forwards a service through an outbound connection.\n")


def proposal(*, source=SOURCE_PATH, create=True, archive=True):
    return {"summary": "Document the lab tunnel with historical context", "archive": archive,
            "coverage": [{"start_line": 1, "end_line": 8, "decision": "create" if create else "covered",
                          "targets": [NEW_NODE if create else "wiki/Concepts/Existing.md"],
                          "reason": "Preserve lab conditions and do not generalize the historical RAID requirement"}],
            "changes": [{"action": "create", "path": NEW_NODE, "description": "Outbound tunnels in the lab",
                         "content": node(source), "evidence": [{"start_line": 3, "end_line": 4,
                         "quote": "The procedure is specific to the lab environment."}]}] if create else []}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "vault"
        self.environment = patch.dict(os.environ, {"DAEDALUS_INGEST_DIR": str(self.base / "state")})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        for area in ("wiki/Concepts", "raw/local", "raw/ai"):
            (self.root / area).mkdir(parents=True)
        (self.root / SOURCE_PATH).write_text(SOURCE)
        (self.root / "wiki/index.md").write_text("# Catalog\n\n## Pages\n- [[Concepts/Existing]]\n")
        (self.root / "wiki/log.md").write_text("# Log\n")
        (self.root / "wiki/Ingestion_Tracker.md").write_text("# Tracker\n")
        (self.root / "wiki/Concepts/Existing.md").write_text(node(title="Existing"))
        self.service = IngestService(self.root)

    def prepared(self, **kwargs):
        return self.service.prepare(SOURCE_PATH, "request-1", **kwargs)

    def reviewed(self, data=None):
        op = self.prepared()
        review = self.service.preview(op["operation_id"], data or proposal())
        return op, review

    def test_full_preview_apply_archive_search_and_idempotent_retry(self):
        engine = SearchEngine(self.root, self.base / "index", interval=0)
        self.addCleanup(engine.close)
        engine.start()
        before = {p: p.read_bytes() for p in self.root.rglob("*.md")}
        op, review = self.reviewed()
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*.md")}, before)
        self.assertIn("raw/local/cataloged/Source.md", review["diff"])
        result = self.service.apply(op["operation_id"], review["proposal_digest"])
        self.assertEqual(result["state"], "committed")
        self.assertEqual(result["search_state"], "search_pending")
        self.assertEqual((self.root / archive_path(SOURCE_PATH)).read_text(), SOURCE)
        self.assertFalse((self.root / SOURCE_PATH).exists())
        self.assertEqual((self.root / "wiki/Concepts/Existing.md").read_bytes(), before[self.root / "wiki/Concepts/Existing.md"])
        self.service.engine = engine
        engine.reindex()
        self.assertEqual(self.service.status(op["operation_id"])["search_state"], "search_ready")
        self.assertIn(NEW_NODE, [r["path"] for r in engine.search("lab tunnel")["results"]])
        docs = engine.catalog()
        self.assertTrue(any(r.target == archive_path(SOURCE_PATH) for r in docs[NEW_NODE].relations))
        after = {p: p.read_bytes() for p in self.root.rglob("*.md")}
        repeated = self.service.apply(op["operation_id"], review["proposal_digest"])
        self.assertEqual(repeated["state"], "committed")
        engine.close()
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*.md")}, after)

    def test_source_paging_targets_and_request_identity(self):
        first = self.prepared(max_chars=12)
        second = self.prepared(start_offset=first["next_offset"], max_chars=24,
                               target_paths=["wiki/Concepts/Existing.md"])
        self.assertEqual(first["operation_id"], second["operation_id"])
        self.assertEqual(first["text"] + second["text"], SOURCE[:36])
        self.assertIn("policy_version", second)
        self.assertEqual(second["target_bytes"]["wiki/Concepts/Existing.md"],
                         (self.root / "wiki/Concepts/Existing.md").stat().st_size)
        (self.root / SOURCE_PATH).write_text(SOURCE + "Changed.\n")
        with self.assertRaises(IngestError):
            self.prepared()

    def test_additive_expansion_preserves_utf8_crlf_and_existing_comments(self):
        path = "wiki/Concepts/Existing.md"
        old = (node(title="Existing") + "\n<!-- approved legacy comment -->\nCafé.\n").replace("\n", "\r\n").encode()
        (self.root / path).write_bytes(old)
        op = self.prepared(target_paths=[path])
        data = proposal(create=False)
        data["coverage"][0]["decision"] = "expand"
        data["changes"] = [{"action": "insert", "path": path,
                            "insertions": [{"offset_utf8": len(old), "text": "\r\n## Lab context\r\nNew supported detail.\r\n"}],
                            "evidence": [{"start_line": 3, "end_line": 4, "quote": "specific to the lab environment"}]}]
        review = self.service.preview(op["operation_id"], data)
        self.service.apply(op["operation_id"], review["proposal_digest"])
        self.assertTrue((self.root / path).read_bytes().startswith(old))

    def test_capture_collisions_empty_slugs_and_repeated_requests(self):
        first = self.service.capture("Rule", "# Synthetic rule\n")
        repeated = self.service.capture("Rule", "# Synthetic rule\n")
        self.assertEqual(first["path"], repeated["path"])
        self.assertTrue(repeated["reused"])
        for title, content in (("Rule", "different content"), ("!!!", "content")):
            with self.assertRaises(IngestError):
                self.service.capture(title, content)
        self.assertEqual((self.root / first["path"]).read_text(), "# Synthetic rule\n")

    def test_failed_capture_does_not_leave_a_partial_raw_note(self):
        with patch.object(application.os, "link", side_effect=OSError("injected full disk")):
            with self.assertRaises(IngestError) as interrupted:
                self.service.capture("New rule", "# A complete new rule\n")
        self.assertEqual(interrupted.exception.code, "failed_recoverable")
        self.assertEqual(list((self.root / "raw/ai").iterdir()), [])
        resumed = self.service.capture("New rule", "# A complete new rule\n")
        self.assertEqual(resumed["publication"]["state"], "pending")

    def test_capture_cannot_add_scanner_exceptions_to_bypass_triage(self):
        marker = '# daedalus-scan: allow CREDENTIAL_ASSIGNMENT value="synthetic.value" reason="Unreviewed"'
        content = marker + "\npassword=" + "synthetic.value" + "\n"
        with self.assertRaises(IngestError):
            self.service.capture("Unreviewed example", content)
        self.assertEqual(list((self.root / "raw/ai").iterdir()), [])

    def test_sources_categories_ambiguity_assets_and_symlinks(self):
        (self.root / "raw/ai/Source.md").write_text(SOURCE)
        (self.root / "raw/assets").mkdir()
        (self.root / "raw/assets/skip.md").write_text("not a source")
        (self.root / "raw/local/link.md").symlink_to(self.root / SOURCE_PATH)
        self.assertEqual(len(self.service.sources()["sources"]), 2)
        self.assertIsNotNone(self.service.sources(limit=1)["next_cursor"])
        with self.assertRaises(IngestError) as ambiguous:
            self.service.prepare("Source", "ambiguous")
        self.assertEqual(ambiguous.exception.code, "ambiguous")
        for path in ("/etc/passwd", "raw/local/../ai/Source.md", "wiki/../../x.md", "raw/local/link.md"):
            with self.assertRaises(IngestError):
                path_for(self.root, path)

    def test_changed_inputs_collision_and_invalidated_review(self):
        op, review = self.reviewed()
        (self.root / NEW_NODE).write_text("User-created note.\n")
        with self.assertRaises(IngestError):
            self.service.apply(op["operation_id"], review["proposal_digest"])
        self.assertEqual((self.root / NEW_NODE).read_text(), "User-created note.\n")
        with self.assertRaises(IngestError):
            self.service.preview(op["operation_id"], {})
        with self.assertRaises(IngestError):
            self.service.apply(op["operation_id"], review["proposal_digest"])

    def test_coverage_evidence_authorship_and_new_links_are_checked(self):
        op = self.prepared()
        variants = []
        item = proposal(); item["coverage"][0]["end_line"] = 7; variants.append(item)
        item = proposal(); item["changes"][0]["evidence"][0]["quote"] = "unsupported claim"; variants.append(item)
        item = proposal(); item["changes"][0]["content"] = node().replace("Autor: [[LLM]]", ""); variants.append(item)
        item = proposal(); item["changes"][0]["content"] += "\n[[Ghost_Concept]]\n"; variants.append(item)
        item = proposal(); item["coverage"][0]["decision"] = "defer"; variants.append(item)
        item = proposal(); item["changes"][0]["action"] = "replace"; variants.append(item)
        for item in variants:
            with self.subTest(proposal=item), self.assertRaises(IngestError):
                self.service.preview(op["operation_id"], item)
        self.assertFalse((self.root / NEW_NODE).exists())

    def test_covered_and_deferred_do_not_force_new_nodes(self):
        op, review = self.reviewed(proposal(create=False))
        self.service.apply(op["operation_id"], review["proposal_digest"])
        self.assertFalse((self.root / NEW_NODE).exists())
        (self.root / "raw/local/Next.md").write_text(SOURCE)
        prepared = self.service.prepare("raw/local/Next.md", "next")
        data = proposal(create=False, archive=False)
        data["coverage"][0].update(decision="defer", targets=[], reason="User must confirm historical context")
        review = self.service.preview(prepared["operation_id"], data)
        self.service.apply(prepared["operation_id"], review["proposal_digest"])
        self.assertTrue((self.root / "raw/local/Next.md").exists())

    def test_already_covered_target_change_invalidates_archival(self):
        op, review = self.reviewed(proposal(create=False))
        path = self.root / "wiki/Concepts/Existing.md"
        changed = b"User replaced the supposedly covered material.\n"
        path.write_bytes(changed)
        with self.assertRaises(IngestError):
            self.service.apply(op["operation_id"], review["proposal_digest"])
        self.assertTrue((self.root / SOURCE_PATH).exists())
        self.assertEqual(path.read_bytes(), changed)

    def test_credentials_require_triage_without_editing_source(self):
        path = self.root / SOURCE_PATH
        path.write_text("password=" + "synthetic.value" + "\n")
        before = path.read_bytes()
        prepared = self.prepared()
        with self.assertRaises(IngestError) as found:
            self.service.preview(prepared["operation_id"], proposal())
        self.assertIn("findings", found.exception.details)
        self.assertEqual(path.read_bytes(), before)

    def test_recovery_before_and_after_every_publication_blocks_indexing(self):
        # Four note/admin publications and one archive creation. Recreate a
        # separate synthetic vault per fault, including a simulated restart.
        for failure in range(1, 6):
            for after in (False, True):
                with self.subTest(failure=failure, after=after):
                    self._recover(failure, after)

    def _recover(self, failure, after):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "vault"
            import shutil
            shutil.copytree(self.root, root)
            service = IngestService(root)
            prepared = service.prepare(SOURCE_PATH, "failure")
            review = service.preview(prepared["operation_id"], proposal())
            engine = SearchEngine(root, Path(temporary) / "index", interval=0)
            engine.start()
            generation = engine.store.current()
            original = application.publish
            calls = 0
            def interrupted(*args):
                nonlocal calls
                calls += 1
                if calls == failure and not after:
                    raise OSError("injected disk failure")
                original(*args)
                if calls == failure and after:
                    raise OSError("injected process interruption")
            try:
                with patch.object(application, "publish", side_effect=interrupted):
                    with self.assertRaises(IngestError):
                        service.apply(prepared["operation_id"], review["proposal_digest"])
                with self.assertRaises(SearchUnavailable):
                    engine.reindex()
                self.assertEqual(engine.store.current(), generation)
                with self.assertRaises(IngestError):
                    service.capture("Another", "No concurrent writes")
                resumed = IngestService(root).apply(prepared["operation_id"], review["proposal_digest"])
                self.assertEqual(resumed["state"], "committed")
                self.assertEqual((root / NEW_NODE).read_text(), node())
                self.assertEqual((root / archive_path(SOURCE_PATH)).read_text(), SOURCE)
                self.assertEqual((root / "wiki/log.md").read_text().count("<!-- ingest:"), 1)
                engine.reindex()
            finally:
                engine.close()

    def test_external_edit_after_interruption_is_not_rolled_back(self):
        op, review = self.reviewed()
        original = application.publish
        def fail_after_first(*args):
            original(*args)
            raise OSError("interrupted")
        with patch.object(application, "publish", side_effect=fail_after_first), self.assertRaises(IngestError):
            self.service.apply(op["operation_id"], review["proposal_digest"])
        changed = (self.root / NEW_NODE).read_bytes() + b"\nUser's later addition.\n"
        (self.root / NEW_NODE).write_bytes(changed)
        with self.assertRaises(IngestError):
            self.service.apply(op["operation_id"], review["proposal_digest"])
        self.assertEqual((self.root / NEW_NODE).read_bytes(), changed)

    def test_operation_owner_and_missing_admin_files(self):
        op = self.prepared()
        other = IngestService(self.root, owner="other")
        with self.assertRaises(IngestError):
            other.preview(op["operation_id"], proposal())
        with self.assertRaises(IngestError):
            other.status(op["operation_id"])
        (self.root / "wiki/log.md").unlink()
        with self.assertRaises(IngestError):
            self.service.preview(op["operation_id"], proposal())
        self.assertTrue((self.root / SOURCE_PATH).exists())

    def test_nested_archive_resolution_and_commit_marker_recovery(self):
        source = "raw/local/nested/Source.md"
        (self.root / source).parent.mkdir()
        (self.root / source).write_text(SOURCE)
        prepared = self.service.prepare(source, "nested")
        review = self.service.preview(prepared["operation_id"], proposal(source=source))
        self.service.apply(prepared["operation_id"], review["proposal_digest"])
        from daedalus_ingest.storage import write_json
        # Simulate interruption after committed journal but before marker removal.
        write_json(state_dir(self.root) / "pending.json", {"operation_id": prepared["operation_id"]})
        resumed = self.service.apply(prepared["operation_id"], review["proposal_digest"])
        self.assertEqual(resumed["state"], "committed")
        self.assertFalse((state_dir(self.root) / "pending.json").exists())
        engine = SearchEngine(self.root, self.base / "index", interval=0)
        try:
            engine.start()
            self.assertTrue(any(r.target == archive_path(source) for r in engine.catalog()[NEW_NODE].relations))
        finally:
            engine.close()

    def test_legacy_helpers_verify_real_nodes_and_source_links(self):
        with self.assertRaises(IngestError):
            self.service.register_node("wiki/Concepts/Missing.md", "missing")
        with self.assertRaises(IngestError):
            self.service.finalize_legacy(SOURCE_PATH, [], [])
        result = self.service.finalize_legacy(SOURCE_PATH, [], ["wiki/Concepts/Existing.md"])
        self.assertEqual(result["state"], "committed")
        result = self.service.finalize_legacy(SOURCE_PATH, [], ["wiki/Concepts/Existing.md"])
        self.assertEqual(result["state"], "committed")
