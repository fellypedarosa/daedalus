"""Shell guard entry point; real Git/deploy scenarios are in tests/ingest."""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "deploy/deploy.sh"


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / ".mcp/deploy").mkdir(parents=True)
        (self.root / ".git").mkdir()
        self.script = self.root / ".mcp/deploy/deploy.sh"
        shutil.copyfile(SCRIPT, self.script)
        commands = self.root / "bin"
        commands.mkdir()
        stub = "#!" + sys.executable + "\n" + '''
import json, os, sys
from pathlib import Path
root = Path(os.environ["DEPLOY_TEST_ROOT"])
if Path(sys.argv[0]).name == "git":
    print(root / ".git/daedalus-deploy.lock")
else:
    with (root / "commands.jsonl").open("a") as log:
        log.write(json.dumps(sys.argv[1:]) + "\\n")
    if os.environ.get("DEPLOY_TEST_APPEND"):
        with (root / ".mcp/deploy/deploy.sh").open("a") as script:
            script.write("\\ntouch should-not-run\\n")
    sys.exit(int(os.environ.get("DEPLOY_TEST_EXIT", "0")))
'''
        for name in ("git", "python3"):
            target = commands / name
            target.write_text(stub)
            target.chmod(0o755)
        self.environment = {**os.environ, "PATH": str(commands) + os.pathsep + os.environ["PATH"],
                            "DEPLOY_TEST_ROOT": str(self.root)}
        for name in ("DEPLOY_TEST_EXIT", "DEPLOY_TEST_APPEND"):
            self.environment.pop(name, None)

    def run_deploy(self, **environment):
        return subprocess.run(["bash", str(self.script)], cwd=self.root,
                              env={**self.environment, **environment},
                              capture_output=True, text=True, timeout=15)

    def test_dispatch_and_exit_status(self):
        for code in (0, 75, 1):
            result = self.run_deploy(DEPLOY_TEST_EXIT=str(code))
            self.assertEqual(result.returncode, code, result.stderr)
        commands = [json.loads(line) for line in (self.root / "commands.jsonl").read_text().splitlines()]
        self.assertEqual(commands, [[".mcp/scripts/sync_ingest.py", "deploy"]] * 3)

    def test_lock_blocks_concurrent_deploy(self):
        with (self.root / ".git/daedalus-deploy.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("já existe um deploy", result.stderr)
        self.assertFalse((self.root / "commands.jsonl").exists())

    def test_updating_script_does_not_execute_appended_commands(self):
        result = self.run_deploy(DEPLOY_TEST_APPEND="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "should-not-run").exists())
