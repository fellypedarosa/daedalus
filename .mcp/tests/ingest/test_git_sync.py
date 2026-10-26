"""Exercise a real bare remote and independent computer/server checkouts."""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from daedalus_ingest.git_sync import GitFailure, Publisher
from daedalus_ingest.publication import file_lock, publication_status, sync_root
from daedalus_ingest.storage import IngestError
from daedalus_search.engine import SearchEngine
from tests.ingest import test_workflow as fixture
from scripts.sync_ingest import deploy
from scripts.migrate_hidden_layout import migrate


@unittest.skipUnless(shutil.which("git"), "Real Git is required")
class GitSyncTests(unittest.TestCase):
    prepared = fixture.WorkflowTests.prepared
    reviewed = fixture.WorkflowTests.reviewed

    def setUp(self):
        fixture.WorkflowTests.setUp(self)
        self.pub = Publisher(self.root)
        self.remote = self.base / "remote.git"
        self.computer = self.base / "computer"
        self.git(self.base, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.root, "init", "--initial-branch=main")
        (self.root / ".gitignore").write_text(".daedalus-sync/\n.env\ntokens.json\n")
        (self.root / "app.py").write_text("version = 1\n")
        self.commit(self.root, "base")
        self.git(self.root, "remote", "add", "origin", str(self.remote))
        self.git(self.root, "push", "origin", "main")
        self.git(self.base, "clone", str(self.remote), str(self.computer))
        self.mark_verified()

    def git(self, directory, *args):
        return subprocess.run(["git", "-c", "user.name=Synthetic test", "-c", "user.email=test@example.invalid",
                               "-C", str(directory), *args], check=True, capture_output=True).stdout

    def commit(self, directory, message):
        self.git(directory, "add", ".")
        self.git(directory, "commit", "-m", message)

    def mark_verified(self):
        self.git(self.computer, "push", "origin", "main:refs/heads/ci/verified-main")

    def apply(self):
        op, review = self.reviewed()
        status = self.service.apply(op["operation_id"], review["proposal_digest"])
        self.assertEqual(status["publication"]["state"], "pending")
        return op["operation_id"]

    def test_automatic_request_publishes_only_approved_files_and_is_idempotent(self):
        operation = self.apply()
        (self.root / "app.py").write_text("version = 99\n")
        self.git(self.root, "add", "app.py")
        (self.root / ".env").write_text("PRIVATE_PLACEHOLDER\n")
        (self.root / "Unrelated.md").write_text("Do not publish.\n")
        result = self.pub.run()
        self.assertEqual(result["state"], "published")
        self.assertEqual(self.git(self.remote, "show", "main:app.py"), b"version = 1\n")
        self.assertEqual(self.git(self.remote, "show", "main:" + fixture.NEW_NODE).decode(), fixture.node())
        self.assertEqual(self.git(self.root, "diff", "--cached", "--name-only").strip(), b"app.py")
        remote_paths = self.git(self.remote, "ls-tree", "-r", "--name-only", "main").decode()
        self.assertNotIn(".env", remote_paths)
        self.assertNotIn("Unrelated.md", remote_paths)
        self.assertNotIn(".daedalus-sync", remote_paths)
        before = self.git(self.remote, "rev-parse", "main")
        self.assertEqual(Publisher(self.root).run()["state"], "idle")
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), before)
        self.assertEqual(self.service.status(operation)["publication"]["state"], "published")

    def test_raw_upload_publishes_only_new_note_and_preserves_unrelated_staging(self):
        original_wiki = self.git(self.remote, "rev-parse", "main:wiki")
        reply = self.service.create_raw_note("clipper", "Upload.md", "# Café\r\nOriginal.\r\n")
        (self.root / "app.py").write_text("version = 99\n")
        self.git(self.root, "add", "app.py")
        (self.root / "raw/ai/Unrelated.md").write_text("Not approved\n")
        self.assertEqual(self.pub.run()["state"], "published")
        self.assertEqual(self.git(self.remote, "show", "main:" + reply["path"]), "# Café\r\nOriginal.\r\n".encode())
        self.assertEqual(self.git(self.remote, "rev-parse", "main:wiki"), original_wiki)
        self.assertEqual(self.git(self.remote, "diff-tree", "--no-commit-id", "--name-only", "-r", "main").decode().strip(), reply["path"])
        self.assertEqual(self.git(self.root, "diff", "--cached", "--name-only").strip(), b"app.py")
        self.assertEqual(self.service.status(reply["operation_id"])["publication"]["state"], "published")
        self.assertEqual(self.pub.run()["state"], "idle")

    def test_publisher_cron_keeps_repository_root_and_journal_from_another_directory(self):
        application = Path(__file__).resolve().parents[2]
        app = self.root / ".mcp"
        (app / "scripts").mkdir(parents=True)
        shutil.copyfile(application / "daedalus_paths.py", app / "daedalus_paths.py")
        shutil.copytree(application / "daedalus_ingest", app / "daedalus_ingest",
                        ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("sync_ingest.py", "auto_backup.sh"):
            shutil.copyfile(application / "scripts" / name, app / "scripts" / name)
        entry = ["bash", str(app / "scripts/auto_backup.sh")]
        self.commit(self.root, "relocated application")
        self.git(self.root, "push", "origin", "main")
        note = self.service.create_raw_note("ai", "Relocated.md", "# Synthetic raw note\n")
        process = subprocess.run(entry, cwd=self.base, check=True, capture_output=True,
                                 text=True, timeout=60)
        self.assertEqual(json.loads(process.stdout)["state"], "published")
        self.assertEqual(self.service.status(note["operation_id"])["publication"]["state"], "published")
        self.assertTrue((app / ".daedalus-sync").is_dir())
        self.assertFalse((self.root / ".daedalus-sync").exists())
        self.assertEqual(self.git(self.remote, "show", "main:raw/ai/Relocated.md"), b"# Synthetic raw note\n")
        again = subprocess.run([sys.executable, str(app / "scripts/sync_ingest.py"), "publish"],
                               cwd=app, check=True, capture_output=True, text=True, timeout=60)
        self.assertEqual(again.stdout.strip(), "")

    def test_raw_upload_and_later_ingestion_publish_as_continuous_history(self):
        reply = self.service.create_raw_note("clipper", "Upload.md", fixture.SOURCE)
        prepared = self.service.prepare(reply["path"], "uploaded-source")
        review = self.service.preview(prepared["operation_id"], fixture.proposal(source=reply["path"]))
        self.service.apply(prepared["operation_id"], review["proposal_digest"])
        self.assertEqual(self.pub.run()["state"], "published")
        self.assertEqual(self.git(self.remote, "show", "main:raw/clipper/cataloged/Upload.md").decode(), fixture.SOURCE)
        paths = self.git(self.remote, "ls-tree", "-r", "--name-only", "main").decode().splitlines()
        self.assertNotIn(reply["path"], paths)
        self.assertEqual(self.service.status(reply["operation_id"])["publication"]["state"], "published")
        self.assertEqual(self.service.status(prepared["operation_id"])["publication"]["state"], "published")

    def test_raw_upload_survives_network_failure_and_conflicts_with_remote_same_name(self):
        reply = self.service.create_raw_note("clipper", "Upload.md", "Server original\n")
        with patch.object(self.pub, "fetch", side_effect=GitFailure("fetch")), self.assertRaises(GitFailure):
            self.pub.run()
        self.assertEqual(self.service.status(reply["operation_id"])["publication"]["state"], "pending")
        self.assertEqual((self.root / reply["path"]).read_text(), "Server original\n")
        target = self.computer / reply["path"]
        target.parent.mkdir(parents=True)
        target.write_text("Computer original\n")
        self.commit(self.computer, "concurrent original")
        self.git(self.computer, "push", "origin", "main")
        with self.assertRaises(IngestError) as conflict:
            self.pub.run()
        self.assertEqual(conflict.exception.code, "conflict")
        self.assertEqual(self.git(self.remote, "show", "main:" + reply["path"]), b"Computer original\n")
        self.assertEqual((self.root / reply["path"]).read_text(), "Server original\n")

    def test_local_code_push_and_server_ingest_merge_without_touching_live_code(self):
        operation = self.apply()
        (self.computer / "app.py").write_text("version = 2\n")
        self.commit(self.computer, "computer update")
        self.git(self.computer, "push", "origin", "main")
        result = self.pub.run()
        self.assertEqual(self.git(self.remote, "show", "main:app.py"), b"version = 2\n")
        self.assertEqual(self.git(self.remote, "show", "main:" + fixture.NEW_NODE).decode(), fixture.node())
        self.assertEqual((self.root / "app.py").read_text(), "version = 1\n")
        self.git(self.root, "pull", "--ff-only", "origin", "main")
        self.assertEqual((self.root / "app.py").read_text(), "version = 2\n")
        self.assertEqual(publication_status(self.root, operation)["published_commit"], result["commit"])

    def test_same_note_conflict_and_source_edit_preserve_server_and_computer(self):
        operation = self.apply()
        path = self.computer / fixture.SOURCE_PATH
        path.write_text(fixture.SOURCE + "Computer added context.\n")
        self.commit(self.computer, "edit source on computer")
        self.git(self.computer, "push", "origin", "main")
        with self.assertRaises(IngestError) as caught:
            self.pub.run()
        self.assertEqual(caught.exception.code, "conflict")
        self.assertEqual(publication_status(self.root, operation)["state"], "conflict")
        self.assertEqual((self.root / fixture.NEW_NODE).read_text(), fixture.node())
        self.assertEqual((self.root / "raw/local/cataloged/Source.md").read_text(), fixture.SOURCE)
        self.assertNotIn("<<<<<<<", (self.root / fixture.NEW_NODE).read_text())
        self.assertIn(b"Computer added context", self.git(self.remote, "show", "main:" + fixture.SOURCE_PATH))

    def test_network_failure_preserves_commit_and_retries_without_duplicate(self):
        operation = self.apply()
        with patch.object(self.pub, "fetch", side_effect=GitFailure("fetch")), self.assertRaises(IngestError):
            self.pub.run()
        saved = self.pub.oid("HEAD")
        self.assertEqual(publication_status(self.root, operation)["state"], "pending")
        self.assertEqual(publication_status(self.root, operation)["commit"], saved)
        Publisher(self.root).run()
        self.assertEqual(self.pub.oid("HEAD"), saved)
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"2")

    def test_restart_after_ref_moves_before_receipt_keeps_one_commit(self):
        self.apply()
        with patch.object(self.pub, "receipt", side_effect=OSError("simulated interruption")), self.assertRaises(OSError):
            self.pub.run()
        saved = self.pub.oid("HEAD")
        Publisher(self.root).run()
        self.assertEqual(self.pub.oid("HEAD"), saved)
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"2")

    def test_pending_publication_survives_state_migration_without_duplicate_commit(self):
        app = self.root / ".mcp"
        (app / "docker-compose.yml").write_text("services: {}\n")
        self.commit(self.root, "new application layout")
        self.git(self.root, "push", "origin", "main")
        operation = self.apply()
        with patch.object(self.pub, "fetch", side_effect=GitFailure("synthetic outage")), self.assertRaises(IngestError):
            self.pub.run()
        saved = self.pub.oid("HEAD")
        current = sync_root(self.root)
        snapshots = {str(p.relative_to(current)): p.read_bytes() for p in current.rglob("*") if p.is_file()}
        current.rename(self.root / ".daedalus-sync")
        with self.assertRaises(IngestError):
            Publisher(self.root)
        migrate(self.root)
        for path, data in snapshots.items():
            self.assertEqual((sync_root(self.root) / path).read_bytes(), data)
        resumed = Publisher(self.root)
        self.assertEqual(resumed.run()["state"], "published")
        self.assertEqual(resumed.oid("HEAD"), saved)
        self.assertEqual(publication_status(self.root, operation)["state"], "published")
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"3")
        self.assertEqual(resumed.run()["state"], "idle")

    def test_successful_push_with_lost_reply_is_detected_by_ancestry(self):
        operation = self.apply()
        original = self.pub.git
        def uncertain(*args, **kwargs):
            result = original(*args, **kwargs)
            if args[0] == "push":
                return subprocess.CompletedProcess([], 1, b"", b"lost response")
            return result
        with patch.object(self.pub, "git", side_effect=uncertain):
            self.pub.run()
        self.assertEqual(publication_status(self.root, operation)["state"], "published")
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"2")

    def test_remote_changes_between_fetch_and_push_are_retried(self):
        self.apply()
        original = self.pub.git
        pushes = []
        def racing(*args, **kwargs):
            if args[0] == "push" and not pushes:
                pushes.append(True)
                (self.computer / "app.py").write_text("version = 3\n")
                self.commit(self.computer, "concurrent update")
                self.git(self.computer, "push", "origin", "main")
            return original(*args, **kwargs)
        with patch.object(self.pub, "git", side_effect=racing):
            self.pub.run()
        self.assertEqual(self.git(self.remote, "show", "main:app.py"), b"version = 3\n")
        self.assertEqual(self.git(self.remote, "show", "main:" + fixture.NEW_NODE).decode(), fixture.node())

    def test_partial_application_blocks_publication_and_deploy(self):
        op, review = self.reviewed()
        with patch.object(fixture.application, "publish", side_effect=OSError("outage")), self.assertRaises(IngestError):
            self.service.apply(op["operation_id"], review["proposal_digest"])
        for method in (self.pub.run, lambda: deploy(self.root)):
            with self.assertRaises(IngestError):
                method()
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"1")

    def test_unapproved_file_changes_and_corrupt_snapshots_block_publication(self):
        operation = self.apply()
        note = self.root / fixture.NEW_NODE
        note.write_text(fixture.node() + "Manual edit.\n")
        with self.assertRaises(IngestError):
            self.pub.run()
        note.write_text(fixture.node())
        request = json.loads((sync_root(self.root) / "operations" / operation / "request.json").read_text())
        checksum = request["changes"][fixture.NEW_NODE]["after"]
        (sync_root(self.root) / "operations" / operation / "blobs" / checksum).write_text("Corrupt snapshot\n")
        with self.assertRaises(IngestError):
            self.pub.run()
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"1")

    def test_multiple_pending_ingestions_preserve_administrative_history(self):
        first = self.apply()
        second_source = "raw/local/Second.md"
        (self.root / second_source).write_text(fixture.SOURCE)
        prepared = self.service.prepare(second_source, "second")
        data = fixture.proposal(source=second_source)
        second_node = "wiki/Concepts/Second.md"
        data["coverage"][0]["targets"] = [second_node]
        data["changes"][0].update(path=second_node, content=fixture.node(second_source, "Second"))
        review = self.service.preview(prepared["operation_id"], data)
        self.service.apply(prepared["operation_id"], review["proposal_digest"])
        self.pub.run()
        log = self.git(self.remote, "show", "main:wiki/log.md").decode()
        self.assertEqual(log.count(first), 1)
        self.assertEqual(log.count(prepared["operation_id"]), 1)
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"3")

    def test_deploy_gate_rejects_writes_but_allows_initial_index_and_readiness(self):
        with file_lock(sync_root(self.root) / "deploy.lock"):
            with self.assertRaises(IngestError) as caught:
                self.service.capture("Rule", "# Synthetic context\n")
            self.assertEqual(caught.exception.code, "busy")
            engine = SearchEngine(self.root, self.base / "index", interval=0)
            try:
                engine.prepare()
                self.assertTrue(engine.status()["ready"])
            finally:
                engine.close()

    def test_deploy_publishes_then_defers_until_new_commit_is_verified(self):
        self.apply()
        self.assertEqual(deploy(self.root), 75)
        with self.assertRaises(IngestError):
            deploy(self.root)
        self.git(self.computer, "pull", "--ff-only", "origin", "main")
        self.mark_verified()
        real_run = subprocess.run
        docker = []
        def run(args, **kwargs):
            if args[0] == "docker":
                docker.append(args)
                if args[4] == "up":
                    # /ready must be able to construct an initial index while
                    # deploy is waiting, and a new ingestion must be refused.
                    with self.assertRaises(IngestError):
                        self.service.capture("Busy", "# Synthetic content\n")
                    engine = SearchEngine(self.root, self.base / "ready-index", interval=0)
                    engine.prepare()
                    self.assertTrue(engine.status()["ready"])
                    engine.close()
                return subprocess.CompletedProcess(args, 0)
            return real_run(args, **kwargs)
        with patch("scripts.sync_ingest.subprocess.run", side_effect=run):
            self.assertEqual(deploy(self.root), 0)
        compose = ["docker", "compose", "-f", str(self.root / ".mcp/docker-compose.yml")]
        self.assertEqual(docker, [[*compose, "build", "daedalus-mcp"],
                                 [*compose, "up", "-d", "--force-recreate", "--wait",
                                  "--wait-timeout", "180", "daedalus-mcp"]])

    def test_unknown_manual_changes_stop_deploy_without_git_pull(self):
        (self.root / "app.py").write_text("Keep this manual edit.\n")
        with self.assertRaises(IngestError):
            deploy(self.root)
        self.assertEqual((self.root / "app.py").read_text(), "Keep this manual edit.\n")

    def test_ignored_ingestion_path_is_not_force_added(self):
        self.apply()
        with (self.root / ".gitignore").open("a") as stream:
            stream.write("wiki/Concepts/Tunnels.md\n")
        with self.assertRaises(IngestError) as caught:
            self.pub.run()
        self.assertIn("ignored", str(caught.exception))
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"1")

    def test_unpublished_manual_commit_is_not_included_even_on_an_approved_path(self):
        with (self.root / "wiki/index.md").open("a") as stream:
            stream.write("Manual unpublished entry.\n")
        self.commit(self.root, "unrelated manual commit")
        self.apply()
        with self.assertRaises(IngestError) as caught:
            self.pub.run()
        self.assertIn("outside the ingestion journal", str(caught.exception))
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"1")

    def test_acknowledged_push_does_not_defer_its_already_verified_workflow(self):
        operation = self.apply()
        real_receipt = self.pub.receipt
        def interrupted(request, **values):
            if values.get("state") == "published":
                raise OSError("interrupted after push")
            return real_receipt(request, **values)
        with patch.object(self.pub, "receipt", side_effect=interrupted), self.assertRaises(OSError):
            self.pub.run()
        self.git(self.computer, "pull", "--ff-only", "origin", "main")
        self.mark_verified()
        real_run = subprocess.run
        def run(args, **kwargs):
            if args[0] == "docker":
                return subprocess.CompletedProcess(args, 0)
            return real_run(args, **kwargs)
        with patch("scripts.sync_ingest.subprocess.run", side_effect=run):
            self.assertEqual(deploy(self.root), 0)
        self.assertEqual(publication_status(self.root, operation)["state"], "published")

    def test_outgoing_push_retries_are_bounded_and_preserved(self):
        operation = self.apply()
        original = self.pub.git
        pushes = []
        def refusing(*args, **kwargs):
            if args[0] == "push":
                pushes.append(True)
                return subprocess.CompletedProcess([], 1, b"", b"network unavailable")
            return original(*args, **kwargs)
        with patch.object(self.pub, "git", side_effect=refusing), self.assertRaises(IngestError):
            self.pub.run()
        self.assertEqual(len(pushes), 3)
        self.assertEqual(publication_status(self.root, operation)["state"], "pending")
        self.assertTrue(self.pub.oid("refs/daedalus/ingest/" + operation))

    def test_pre_queue_operation_retry_does_not_retroactively_publish(self):
        prepared, review = self.reviewed()
        self.service.apply(prepared["operation_id"], review["proposal_digest"])
        # Simulate a completed journal from the version without publication.
        shutil.rmtree(sync_root(self.root) / "operations")
        result = self.service.apply(prepared["operation_id"], review["proposal_digest"])
        self.assertEqual(result["publication"]["state"], "not_requested")
        self.assertEqual(Publisher(self.root).run()["state"], "idle")

    def test_retained_source_edited_remotely_requires_review(self):
        prepared, review = self.reviewed(fixture.proposal(archive=False))
        self.service.apply(prepared["operation_id"], review["proposal_digest"])
        (self.computer / fixture.SOURCE_PATH).write_text(fixture.SOURCE + "New source version.\n")
        self.commit(self.computer, "updated source")
        self.git(self.computer, "push", "origin", "main")
        with self.assertRaises(IngestError) as caught:
            self.pub.run()
        self.assertEqual(caught.exception.code, "conflict")
        self.assertEqual((self.root / fixture.SOURCE_PATH).read_text(), fixture.SOURCE)

    def test_restart_during_real_index_refresh_recovers_without_extra_commit(self):
        self.apply()
        original = self.pub.git
        def interrupted(*args, **kwargs):
            if args[0] == "update-index" and not kwargs.get("env"):
                raise OSError("interrupted index refresh")
            return original(*args, **kwargs)
        with patch.object(self.pub, "git", side_effect=interrupted), self.assertRaises(OSError):
            self.pub.run()
        Publisher(self.root).run()
        self.assertEqual(self.git(self.remote, "rev-list", "--count", "main").strip(), b"2")
        self.assertFalse(self.git(self.root, "diff", "--cached", "--name-only").strip())

    def test_build_or_readiness_failure_stops_and_releases_maintenance_gate(self):
        real_run = subprocess.run
        for stage, expected in (("build", 1), ("up", 2)):
            with self.subTest(stage=stage):
                calls = []
                def run(args, **kwargs):
                    if args[0] == "docker":
                        calls.append(args)
                        if args[4] == stage:
                            raise subprocess.CalledProcessError(1, args)
                        return subprocess.CompletedProcess(args, 0)
                    return real_run(args, **kwargs)
                with patch("scripts.sync_ingest.subprocess.run", side_effect=run), self.assertRaises(subprocess.CalledProcessError):
                    deploy(self.root)
                self.assertEqual(len(calls), expected)
                prepared = self.service.prepare(fixture.SOURCE_PATH, "maintenance-released-" + stage)
                self.assertEqual(prepared["state"], "prepared")


if __name__ == "__main__":
    unittest.main()
