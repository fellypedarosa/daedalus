"""Exercise the relocated app against a synthetic repository, not real notes."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from daedalus_paths import APP_DIR, POLICY_PATH
from tests.ingest.test_mcp import setup, unpack
from tests.ingest.test_workflow import SOURCE_PATH, SOURCE, node


class LayoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_vault_policy_and_cli_do_not_depend_on_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, environment = setup(base)
            app = root / ".mcp"
            app.mkdir()
            # Only application source is copied; credentials/state are never fixtures.
            for name in ("daedalus_mcp.py", "daedalus_paths.py", "daedalus.py"):
                shutil.copyfile(APP_DIR / name, app / name)
            for name in ("daedalus_search", "daedalus_ingest", "daedalus_validation"):
                shutil.copytree(APP_DIR / name, app / name, ignore=shutil.ignore_patterns("__pycache__"))
            policy = POLICY_PATH.read_text()
            (app / "INGEST.md").write_text(policy)
            (root / "wiki/Concepts/Existing.md").write_text(node(title="Existing"))
            # No explicit vault configuration: the relocated app must find its parent.
            env = {**os.environ, **environment}
            env.pop("DAEDALUS_VAULT_DIR", None)
            env.pop("DAEDALUS_TEST_AUDIT_LOG", None)
            for cwd in (root, app, base):
                with self.subTest(cwd=str(cwd)):
                    transport = StdioTransport(command=sys.executable, args=[str(app / "daedalus_mcp.py")],
                        env=env, cwd=str(cwd), log_file=base / "layout-server.log")
                    async with Client(transport, timeout=40) as client:
                        proof = unpack(await client.call_tool("test"))
                        self.assertEqual(proof["status"], "MCP_CONNECTED")
                        overview = unpack(await client.call_tool("summary"))
                        self.assertEqual(overview["total_nodes"], 1)
                        prepared = unpack(await client.call_tool("ingest_prepare", {
                            "source_path": SOURCE_PATH, "request_id": "layout-default-root"}))
                        self.assertEqual(prepared["text"], SOURCE)
                        self.assertEqual(prepared["policy"], policy)
                    cli = subprocess.run([sys.executable, str(app / "daedalus.py"), "summary", "--format", "json"],
                                         cwd=cwd, env=env, capture_output=True, text=True, check=True, timeout=30)
                    self.assertEqual(json.loads(cli.stdout)["total_nodes"], 1)
            self.assertTrue((app / ".mcp_test_audit.jsonl").is_file())
            self.assertFalse((root / ".mcp_test_audit.jsonl").exists())
