"""Raw upload is immutable, resumable, and independent from editorial ingestion."""
import json
import unittest
from unittest.mock import patch

from daedalus_ingest import apply as application
from daedalus_ingest import capture
from daedalus_ingest.publication import sync_root
from daedalus_ingest.service import IngestService
from daedalus_ingest.storage import IngestError, sha, state_dir, write_json
from tests.ingest import test_workflow as fixture


class RawNoteTests(unittest.TestCase):
    setUp = fixture.WorkflowTests.setUp

    def create(self, category="clipper", filename="Anotação original.md", content="# Café\r\n\r\nTexto.\r\n"):
        return self.service.create_raw_note(category, filename, content)

    def test_all_categories_preserve_filename_utf8_crlf_and_only_create_raw(self):
        original = {p: p.read_bytes() for p in self.root.rglob("*.md")}
        for category in ("ai", "clipper", "youtube", "local"):
            reply = self.create(category)
            data = "# Café\r\n\r\nTexto.\r\n".encode()
            self.assertEqual((self.root / reply["path"]).read_bytes(), data)
            self.assertEqual(reply["sha256"], sha(data))
            self.assertEqual(reply["bytes"], len(data))
            self.assertEqual(reply["state"], "saved")
            self.assertFalse(reply["ingestion_requested"])
            self.assertFalse(reply["reused"])
            self.assertEqual(reply["publication"]["state"], "pending")
            request = json.loads((sync_root(self.root) / "operations" / reply["operation_id"] / "request.json").read_text())
            self.assertEqual(request["changes"], {reply["path"]: {"before": None, "after": sha(data)}})
            self.assertEqual(request["dependencies"], {})
        self.assertTrue(all(p.read_bytes() == data for p, data in original.items()))
        self.assertFalse(any((self.root / "raw").rglob("cataloged")))
        self.assertIn("raw/clipper/Anotação original.md", [s["path"] for s in self.service.sources()["sources"]])

    def test_repeat_and_collision_do_not_overwrite_or_duplicate_queue(self):
        first = self.create()
        repeated = self.create()
        self.assertTrue(repeated["reused"])
        self.assertEqual(first["operation_id"], repeated["operation_id"])
        self.assertEqual(len(list((sync_root(self.root) / "operations").iterdir())), 1)
        with self.assertRaises(IngestError):
            self.create(content="Different")
        self.assertEqual((self.root / first["path"]).read_bytes(), "# Café\r\n\r\nTexto.\r\n".encode())

    def test_existing_and_archived_notes_are_reused_without_retroactive_publication(self):
        for cataloged in (False, True):
            path = self.root / "raw/clipper" / ("cataloged" if cataloged else "") / "Existing.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"Existing original\r\n")
            reply = self.create(filename="Existing.md", content="Existing original\r\n")
            self.assertTrue(reply["reused"])
            self.assertEqual(reply["cataloged"], cataloged)
            self.assertEqual(reply["publication"]["state"], "not_requested")
            self.assertIsNone(reply["operation_id"])
            with self.assertRaises(IngestError):
                self.create(filename="Existing.md", content="Changed")
            path.unlink()

    def test_repeated_upload_does_not_recreate_an_archived_note(self):
        first = self.create()
        source = self.root / first["path"]
        archive = source.parent / "cataloged" / source.name
        archive.parent.mkdir()
        source.rename(archive)
        repeated = self.create()
        self.assertEqual(repeated["path"], archive.relative_to(self.root).as_posix())
        self.assertTrue(repeated["cataloged"])
        self.assertFalse(source.exists())

    def test_invalid_category_names_traversal_control_characters_and_size(self):
        for category, filename, content in (
            ("assets", "Note.md", "Text"), ("../wiki", "Note.md", "Text"),
            ("clipper", "../Note.md", "Text"), ("clipper", "/tmp/Note.md", "Text"),
            ("ai", "cataloged/Note.md", "Text"), ("ai", "Note\\other.md", "Text"),
            ("ai", "Note.txt", "Text"), ("ai", "Bad\nname.md", "Text"),
            ("ai", "Bad#name.md", "Text"), ("ai", ".md", "Text"),
            ("ai", "x" * 241 + ".md", "Text"), ("ai", "Empty.md", " \n"),
            ("ai", "Large.md", "é" * 1_000_001),
        ):
            with self.subTest(category=category, filename=filename[:30]), self.assertRaises(IngestError):
                self.create(category, filename, content)
        self.assertFalse((state_dir(self.root) / "pending.json").exists())

    def test_symbolic_links_are_rejected(self):
        (self.root / "raw/clipper").symlink_to(self.root / "wiki", target_is_directory=True)
        with self.assertRaises(IngestError):
            self.create()
        (self.root / "raw/clipper").unlink()
        (self.root / "raw/clipper").mkdir()
        (self.root / "raw/clipper/Anotação original.md").symlink_to(self.root / fixture.SOURCE_PATH)
        with self.assertRaises(IngestError):
            self.create()

    def test_interruption_before_creation_resumes_and_blocks_unrelated_writes(self):
        with patch.object(application, "publish", side_effect=OSError("synthetic full disk")):
            with self.assertRaises(IngestError) as interrupted:
                self.create()
        operation = interrupted.exception.details["operation_id"]
        self.assertEqual(self.service.status(operation)["state"], "failed_recoverable")
        with self.assertRaises(IngestError):
            self.create(filename="Another.md")
        self.assertFalse(list((self.root / "raw/clipper").glob("*.md")))
        resumed = self.create()
        self.assertEqual(resumed["operation_id"], operation)
        self.assertEqual(resumed["publication"]["state"], "pending")
        self.assertFalse((state_dir(self.root) / "pending.json").exists())

    def test_interruption_after_creation_resumes_without_overwrite(self):
        with patch.object(capture, "finish_request", side_effect=OSError("synthetic outage")):
            with self.assertRaises(IngestError):
                self.create()
        with patch.object(application, "publish", side_effect=AssertionError("Must not rewrite")):
            self.assertEqual(self.create()["publication"]["state"], "pending")

    def test_committed_retry_clears_marker_left_by_process_exit(self):
        first = self.create()
        marker = state_dir(self.root) / "pending.json"
        write_json(marker, {"operation_id": first["operation_id"]})
        self.create()
        self.assertFalse(marker.exists())
        self.create(filename="Another.md")

    def test_owner_isolation_and_no_ingest_apply_or_preview_on_capture(self):
        first = self.create()
        other = IngestService(self.root, owner="other")
        with self.assertRaises(IngestError) as forbidden:
            other.status(first["operation_id"])
        self.assertEqual(forbidden.exception.code, "forbidden")
        with self.assertRaises(IngestError):
            self.service.apply(first["operation_id"], "irrelevant")
        with self.assertRaises(IngestError):
            self.service.preview(first["operation_id"], fixture.proposal())
        self.assertEqual(self.service.status(first["operation_id"])["state"], "saved")

    def test_credentials_cannot_be_uploaded_or_hidden_by_new_exception_markers(self):
        for content in ("password=" + "synthetic.value\n",
                        '# daedalus-scan: allow CREDENTIAL_ASSIGNMENT value="synthetic.value" reason="Unreviewed"\n'
                        + "password=" + "synthetic.value\n"):
            with self.assertRaises(IngestError):
                self.create(content=content)
        self.assertFalse(list((self.root / "raw").rglob("Anotação original.md")))
