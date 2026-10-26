"""The opt-in installer edits only this checkout's publication schedule."""
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import install_ingest_sync as installer


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project space"
        self.root.mkdir()

    def install(self, existing="", code=0, error=""):
        calls = []
        def run(args, **kwargs):
            calls.append((args, kwargs))
            if args == ["crontab", "-l"]:
                return subprocess.CompletedProcess(args, code, existing, error)
            return subprocess.CompletedProcess(args, 0)
        with patch.object(installer, "ROOT", self.root), patch.object(installer.subprocess, "run", side_effect=run):
            installer.main()
        return calls

    def test_replaces_legacy_job_preserves_other_jobs_and_quotes_paths(self):
        script = self.root / "scripts/auto_backup.sh"
        previous = "# Existing configuration\n0 2 * * * /bin/true\n*/15 * * * * /bin/bash '" + str(script) + "'\n"
        calls = self.install(previous)
        text = calls[-1][1]["input"]
        self.assertIn("0 2 * * * /bin/true", text)
        self.assertNotIn("*/15", text)
        self.assertEqual(text.count("auto_backup.sh"), 1)
        self.assertIn(".mcp/scripts/auto_backup.sh", text)
        self.assertIn("* * * * * /bin/bash '", text)
        backup = self.root / ".mcp/.daedalus-sync/crontab.before"
        self.assertEqual(backup.read_text(), previous)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertEqual(self.install(text)[-1][1]["input"], text)

    def test_absent_crontab_is_supported_but_read_errors_are_not(self):
        self.assertEqual(self.install(code=1, error="no crontab for synthetic")[-1][0], ["crontab", "-"])
        with self.assertRaises(SystemExit):
            self.install(code=1, error="permission denied")

    def test_does_not_silently_remove_another_checkouts_job(self):
        previous = "* * * * * /bin/bash /another/project/scripts/auto_backup.sh " + installer.MARKER + "\n"
        with self.assertRaises(SystemExit):
            self.install(previous)

    def test_new_and_legacy_entries_converge_to_one_new_job(self):
        old = self.root / "scripts/auto_backup.sh"
        new = self.root / ".mcp/scripts/auto_backup.sh"
        middle = self.root / "MCP/scripts/auto_backup.sh"
        previous = f"*/15 * * * * /bin/bash '{old}'\n* * * * * /bin/bash '{middle}'\n* * * * * /bin/bash '{new}'\n"
        text = self.install(previous)[-1][1]["input"]
        self.assertEqual(text.count("auto_backup.sh"), 1)
        self.assertIn(str(new), text)
        self.assertNotIn("*/15", text)

    def test_legacy_state_is_not_silently_replaced(self):
        (self.root / ".daedalus-sync").mkdir()
        with self.assertRaises(SystemExit):
            self.install()
        self.assertFalse((self.root / ".mcp/.daedalus-sync").exists())
