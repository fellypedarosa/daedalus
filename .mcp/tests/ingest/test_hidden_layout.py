"""A stopped server can relocate private state without losing queued work."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.migrate_hidden_layout import assert_quiet, migrate, plan
from daedalus_ingest.publication import file_lock, sync_root
from daedalus_ingest.storage import IngestError


@unittest.skipUnless(shutil.which("git"), "Real Git is required")
class HiddenLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project space"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".mcp").mkdir()
        (self.root / ".mcp/docker-compose.yml").write_text("services: {}\n")
        self.state = self.root / ".daedalus-sync"
        (self.state / "operations/example/blobs").mkdir(parents=True)
        (self.state / "operations/example/request.json").write_text(json.dumps({"state": "pending"}))
        (self.state / "operations/example/blobs/snapshot").write_bytes(b"Original\r\n")
        (self.state / "receipts").mkdir()
        self.state.chmod(0o700)

    def test_inspection_is_read_only_and_apply_preserves_private_bytes_and_permissions(self):
        old = self.root / "MCP"
        (old / "tmp").mkdir(parents=True)
        (old / "tokens.json").write_text("<SYNTHETIC_PRIVATE_CONFIG>")
        (old / "tokens.json").chmod(0o600)
        (old / "tmp/study.md").write_text("Private study\n")
        cache = old / "daedalus_ingest/__pycache__"
        cache.mkdir(parents=True)
        (cache / "old.pyc").write_bytes(b"old cache")
        planned = plan(self.root)
        self.assertTrue(planned)
        self.assertTrue(self.state.exists())
        self.assertFalse((self.root / ".mcp/tokens.json").exists())
        self.assertGreater(migrate(self.root), 0)
        self.assertEqual((self.root / ".mcp/tokens.json").read_text(), "<SYNTHETIC_PRIVATE_CONFIG>")
        self.assertEqual((self.root / ".mcp/tokens.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / ".mcp/.daedalus-sync").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / ".mcp/.daedalus-sync/operations/example/blobs/snapshot").read_bytes(), b"Original\r\n")
        self.assertEqual((self.root / ".mcp/tmp/migracao-layout/MCP/daedalus_ingest/__pycache__/old.pyc").read_bytes(), b"old cache")
        self.assertFalse(old.exists())
        self.assertFalse(self.state.exists())
        self.assertEqual(migrate(self.root), 0)

    def test_collision_or_incomplete_operation_stops_before_any_private_move(self):
        old = self.root / "MCP"
        old.mkdir()
        (old / "tokens.json").write_text("<OLD_CONFIG>")
        (self.root / ".mcp/tokens.json").write_text("<NEW_CONFIG>")
        with self.assertRaises(ValueError):
            migrate(self.root)
        self.assertTrue(self.state.exists())
        self.assertEqual((old / "tokens.json").read_text(), "<OLD_CONFIG>")
        (self.root / ".mcp/tokens.json").unlink()
        (self.state / "operations/example/request.json").write_text(json.dumps({"state": "applying"}))
        with self.assertRaises(ValueError):
            migrate(self.root)
        self.assertFalse((self.root / ".mcp/tokens.json").exists())

    def test_existing_new_state_and_symlinks_are_never_merged(self):
        (self.root / ".mcp/.daedalus-sync").mkdir()
        with self.assertRaises(ValueError):
            plan(self.root)
        (self.root / ".mcp/.daedalus-sync").rmdir()
        (self.state / "operations/link").symlink_to(self.root / ".git", target_is_directory=True)
        with self.assertRaises(ValueError):
            plan(self.root)

    def test_default_publisher_refuses_legacy_state_instead_of_creating_empty_state(self):
        with patch.dict(os.environ, {"DAEDALUS_SYNC_DIR": ""}):
            with self.assertRaises(IngestError) as caught:
                sync_root(self.root)
        self.assertEqual(caught.exception.code, "migration_required")
        self.assertFalse((self.root / ".mcp/.daedalus-sync").exists())

    def test_active_publisher_lock_stops_before_any_move(self):
        with file_lock(self.state / "writer.lock"):
            with self.assertRaises(BlockingIOError):
                migrate(self.root)
        self.assertTrue(self.state.exists())
        self.assertFalse((self.root / ".mcp/.daedalus-sync").exists())

    def test_unexpected_old_source_and_future_archive_collision_require_review(self):
        old = self.root / "MCP"
        old.mkdir()
        (old / "unexpected.py").write_text("# Preserve this manual file\n")
        with self.assertRaises(ValueError):
            plan(self.root)
        (old / "unexpected.py").unlink()
        (old / "__pycache__").mkdir()
        (old / "__pycache__/old.pyc").write_bytes(b"cache")
        destination = old / "tmp/migracao-layout/MCP/__pycache__"
        destination.mkdir(parents=True)
        with self.assertRaises(ValueError):
            plan(self.root)
        self.assertTrue(self.state.exists())

    def test_server_checks_reject_running_container_and_active_cron(self):
        container = [{"State": {"Running": True}, "Mounts": [
            {"Destination": "/vault/wiki", "Source": str(self.root / "wiki")}]}]
        with patch("scripts.migrate_hidden_layout.run", side_effect=[str(self.root), "", json.dumps(container)]):
            with self.assertRaisesRegex(ValueError, "Pare o container"):
                assert_quiet(self.root)
        container[0]["State"]["Running"] = False
        cron = subprocess.CompletedProcess([], 0, "* * * * * job # daedalus-ingest-publisher\n", "")
        with patch("scripts.migrate_hidden_layout.run", side_effect=[str(self.root), "", json.dumps(container)]), \
             patch("scripts.migrate_hidden_layout.subprocess.run", return_value=cron):
            with self.assertRaisesRegex(ValueError, "agendamento"):
                assert_quiet(self.root)
